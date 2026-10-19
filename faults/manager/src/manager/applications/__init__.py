import asyncio
import logging
import subprocess
import time
import httpx
import random

from datetime import datetime, timedelta
from httpx import AsyncClient, AsyncHTTPTransport, Timeout
from pathlib import Path

from ..kpis.prometheus import (
    PrometheusMetric,
    LOCUST_LATENCY_95_TEMPLATE,
    LOCUST_USERS_TEMPLATE,
    LOCUST_ERROR_RATE_TEMPLATE,
    CONTAINER_START_WINDOW_TEMPLATE,
)


logger = logging.getLogger(__name__)


class Application:


    def __init__(self, manifests_path: Path, microservice_benchmark: str, locust_url: str, prometheus_client: AsyncClient, slo_error_rate: float = 0.05):
        self.manifests_path = manifests_path
        self.microservice_benchmark = microservice_benchmark
        
        self.locust_client = AsyncClient(base_url=locust_url, transport=AsyncHTTPTransport(retries=10), timeout=Timeout(10, connect=30))

        # To be set dynamically with create_baseline_latency
        self.baseline_latency = []

        self.metric_user_count = PrometheusMetric(prometheus_client, LOCUST_USERS_TEMPLATE.render(
            service=f"locust-{microservice_benchmark}"
        ))

        self.metric_latency = PrometheusMetric(prometheus_client, LOCUST_LATENCY_95_TEMPLATE.render(
            service=f"locust-{microservice_benchmark}"
        ))
        self.slo_error_rate = slo_error_rate
        self.metric_error_rate = PrometheusMetric(prometheus_client, LOCUST_ERROR_RATE_TEMPLATE.render(
            service=f"locust-{microservice_benchmark}"
        ))
        self.metric_container_restarts = PrometheusMetric(prometheus_client, CONTAINER_START_WINDOW_TEMPLATE.render(
            namespace=microservice_benchmark
        ))

    def deploy(self) -> bool:
        '''Creates the application's k8s resources. Returns `True` if it succeeds and `False` otherwise'''

        # This command is already asynchronous.
        # We do care if creating any of the kubernetes resources fails.
        logger.info(f"creating {self.microservice_benchmark} k8s resources")
        completed_process = subprocess.run(
            f"kubectl apply -f {self.manifests_path}/{self.microservice_benchmark}/application.yaml -f {self.manifests_path}/{self.microservice_benchmark}/load.yaml",
            shell=True,
            check=False, # we don't want an exception to be raised non-zero exit code
            capture_output=True
        )
        if completed_process.returncode != 0:
            logger.warning(f"kubectl did not exit successfully: stdout[{completed_process.stdout}] stderr[{completed_process.stderr}]")
            return False

        logger.info(f"{self.microservice_benchmark} k8s resources created")
        return True


    async def wait_for_ready(self):
        logger.info(f"waiting for {self.microservice_benchmark} resources to be available")
        process = await asyncio.create_subprocess_exec(
            "kubectl", "wait", f"--namespace={self.microservice_benchmark}", "deploy", "--all", "--for=condition=Available", "--timeout=120s",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.wait()
        if process.returncode != 0:
            stdout = await process.stdout.read()
            stderr = await process.stderr.read()
            logger.warning(f"kubectl process did not exit successfully: stdout[{stdout}] stderr[{stderr}]")
            return False

        process = await asyncio.create_subprocess_exec(
            "kubectl", "wait", f"--namespace=load-generators-{self.microservice_benchmark}", "deploy", "--all", "--for=condition=Available", "--timeout=120s",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.wait()
        if process.returncode != 0:
            stdout = await process.stdout.read()
            stderr = await process.stderr.read()
            logger.warning(f"kubectl process did not exit successfully: stdout[{stdout}] stderr[{stderr}]")
            return False
        logger.info(f"{self.microservice_benchmark} resources are available")

        logger.info(f"waiting for {self.microservice_benchmark} jobs to complete")
        process = await asyncio.create_subprocess_exec(
            "kubectl", "wait", f"--namespace={self.microservice_benchmark}",
            "job", "--all", "--for=condition=Complete", "--timeout=300s",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.wait()
        if process.returncode != 0:
            stdout = await process.stdout.read()
            stderr = await process.stderr.read()
            logger.warning(f"kubectl process did not exit successfully: stdout[{stdout}] stderr[{stderr}]")
            return False
        logger.info(f"{self.microservice_benchmark} jobs have completed")

        return True

    def destroy(self):
        '''Deletes the application's k8s resources. Returns `True` if it succeeds and `False` otherwise'''

        logger.info(f"deleting {self.microservice_benchmark} k8s resources")
        completed_process = subprocess.run(
            f"kubectl delete -f {self.manifests_path}/{self.microservice_benchmark}/application.yaml -f {self.manifests_path}/{self.microservice_benchmark}/load.yaml",
            shell=True,
            check=False, # we don't want an exception to be raised on non-zero exit code
            capture_output=True
        )
        if completed_process.returncode != 0:
            logger.warning(f"kubectl did not exit successfully: stdout[{completed_process.stdout}] stderr[{completed_process.stderr}]")
            return False

        logger.info(f"{self.microservice_benchmark} k8s resources deleted")
        return True

    async def set_load(self, users: int, timeout: timedelta = timedelta(minutes=5), backoff_interval: timedelta = timedelta(seconds=10)):
        end = datetime.now() + timeout
        logger.info(f"{self.microservice_benchmark} setting load to {users}")

        while datetime.now() < end:
            res = await self.locust_client.post(
                "/swarm",
                data={"user_count": users, "spawn_rate": 20}
            )

            if res.status_code != httpx.codes.OK:
                logger.error(f"locust swarm failed: {res.status_code} {res.text}")
                raise Exception("Locust")

            res = await self.metric_user_count.query()
            if not res:
                continue

            current_users = int(res[0]["value"][1])
            if (current_users == users):
                logger.info(f"{self.microservice_benchmark} load set to {users}")
                return True

            logger.info(f"{self.microservice_benchmark} current load {current_users} != {users} desired. Retrying")
            await asyncio.sleep(backoff_interval.total_seconds())

        logger.error(f"failed to set {self.microservice_benchmark} load to {users} users")
        return False

    async def stop_load(self):
        res = await self.locust_client.get("/stop")
        if res.status_code != httpx.codes.OK:
            logger.error(f"locust swarm failed: {res.status_code} {res.text}")
            raise Exception("Locust")

    async def create_baseline_latency(
        self, timeout: timedelta = timedelta(minutes=5), baseline_interval: timedelta = timedelta(minutes=1), backoff_interval: timedelta = timedelta(seconds=10)
    ):
        end = datetime.now() + timeout
        logger.info(f"creating {self.microservice_benchmark} baseline")
        while datetime.now() < end:
            end_epoch = time.time()
            start_epoch = end_epoch - baseline_interval.total_seconds()

            res = await self.metric_error_rate.query_range(start_epoch, end_epoch)
            if not res:
                logger.info(f"{self.microservice_benchmark} no error rate data: {res}")
                await asyncio.sleep(backoff_interval.total_seconds())
                continue
            errors = [float(val) for _, val in res[0]['values'] if float(val) > self.slo_error_rate]
            if len(errors) > 0:
                logger.info(f"{self.microservice_benchmark} error rate exceeds slo {self.slo_error_rate} between [{start_epoch}; {end_epoch}]")
                logger.debug(f"errors: {errors}")
                await asyncio.sleep(backoff_interval.total_seconds())
                continue

            res = await self.metric_container_restarts.query_range(start_epoch, end_epoch)
            if not res:
                await asyncio.sleep(backoff_interval.total_seconds())
                logger.info(f"{self.microservice_benchmark} no container restarts data")
                continue
            container_restarts = [int(val) for _, val in res[0]['values'] if int(val) > 0]
            if len(container_restarts) > 0:
                logger.info(f"{self.microservice_benchmark} had {len(container_restarts)} container restarts between [{start_epoch}; {end_epoch}]")
                await asyncio.sleep(backoff_interval.total_seconds())
                continue

            res = await self.metric_latency.query_range(start_epoch, end_epoch)
            if not res:
                logger.info(f"{self.microservice_benchmark} no latency data")
                await asyncio.sleep(backoff_interval.total_seconds())
                continue
            latencies = res[0]['values']
            if len(latencies) < baseline_interval.total_seconds():
                logger.info(f"not enough samples for baseline latency: {len(latencies)} < {baseline_interval.total_seconds()}")
                await asyncio.sleep(backoff_interval.total_seconds())
                continue
            logger.info(f"{self.microservice_benchmark}: create new latency baseline")
            latencies = [float(val) for _, val in latencies]
            self.baseline_latency = latencies
            return True
        return False
