import asyncio
import logging
import subprocess
import time
import httpx
import random
from httpx_retries import Retry, RetryTransport
import numpy as np

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
from ..kpis import stats


logger = logging.getLogger(__name__)


class Application:


    def __init__(self, manifests_path: Path, microservice_benchmark: str, locust_url: str, prometheus_client: AsyncClient, slo_error_rate: float = 0.05):
        self.manifests_path = manifests_path
        self.microservice_benchmark = microservice_benchmark

        retry = Retry(
            total=10,
            backoff_factor=0.5,
            max_backoff_wait=30,
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        transport = RetryTransport(retry=retry)
        self.locust_client = AsyncClient(base_url=locust_url, transport=transport, timeout=Timeout(10, connect=30))

        # To be set dynamically with create_baseline_latency
        self.baseline_latency = []
        self.load = 0

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

        self.baseline_latency = []
        logger.info(f"{self.microservice_benchmark} k8s resources created")
        return True

    def deploy_load(self) -> bool:
        '''Creates the application's load generator k8s resources. Returns `True` if it succeeds and `False` otherwise'''

        # This command is already asynchronous.
        # We do care if creating any of the kubernetes resources fails.
        logger.info(f"creating {self.microservice_benchmark} load generator k8s resources")
        completed_process = subprocess.run(
            f"kubectl apply -f {self.manifests_path}/{self.microservice_benchmark}/load.yaml",
            shell=True,
            check=False, # we don't want an exception to be raised non-zero exit code
            capture_output=True
        )
        if completed_process.returncode != 0:
            logger.warning(f"kubectl did not exit successfully: stdout[{completed_process.stdout}] stderr[{completed_process.stderr}]")
            return False

        logger.info(f"{self.microservice_benchmark} load generator k8s resources created")
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
            logger.info(f"kubectl wait {self.microservice_benchmark} jobs output: stdout[{stdout}] stderr[{stderr}]")
        logger.info(f"{self.microservice_benchmark} jobs have completed")

        return True

    def destroy_load(self):
        '''Deletes the application's load generator k8s resources. Returns `True` if it succeeds and `False` otherwise'''

        logger.info(f"deleting {self.microservice_benchmark} load generator k8s resources")
        completed_process = subprocess.run(
            f"kubectl delete -f {self.manifests_path}/{self.microservice_benchmark}/load.yaml",
            shell=True,
            check=False, # we don't want an exception to be raised on non-zero exit code
            capture_output=True
        )
        if completed_process.returncode != 0:
            logger.warning(f"kubectl did not exit successfully: stdout[{completed_process.stdout}] stderr[{completed_process.stderr}]")
            return False

        logger.info(f"{self.microservice_benchmark} load generator k8s resources deleted")
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

        self.baseline_latency = []
        logger.info(f"{self.microservice_benchmark} k8s resources deleted")
        return True

    async def set_load(
        self,
        users: int,
        spawn_rate: int = 20,
        timeout: timedelta = timedelta(seconds=30),
        backoff_interval: timedelta = timedelta(seconds=10),
        attempts: int = 1
    ):
        logger.debug(f"{self.microservice_benchmark} setting load to {users}")
        for i in range(attempts):
            end = datetime.now() + timeout

            while datetime.now() < end:
                try:
                    res = await self.locust_client.post(
                        "/swarm",
                        data={"user_count": users, "spawn_rate": spawn_rate}
                    )
                except Exception as e:
                    logger.warning(f"{self.microservice_benchmark} failed locust post request. Exception: {e}")
                    await asyncio.sleep(backoff_interval.total_seconds())
                    continue

                if res.status_code != httpx.codes.OK:
                    logger.error(f"locust swarm failed: {res.status_code} {res.text}")
                    await asyncio.sleep(backoff_interval.total_seconds())
                    continue

                res = await self.metric_user_count.query()
                if not res:
                    await asyncio.sleep(backoff_interval.total_seconds())
                    continue

                current_users = int(res[0]["value"][1])
                if (current_users == users):
                    self.load = users
                    logger.info(f"{self.microservice_benchmark} load set to {users}")
                    return True

                logger.debug(f"{self.microservice_benchmark} current load {current_users} != {users} desired. Retrying")
                await asyncio.sleep(backoff_interval.total_seconds())

            if i == attempts-1:
                raise Exception(f"Failed to set load for {self.microservice_benchmark}")

            logger.info("failed to set load within deadline. Restarting load generator.")
            self.destroy_load()
            self.deploy_load()
            await self.wait_for_ready()

        logger.error(f"failed to set {self.microservice_benchmark} load to {users} users")
        return False

    async def stop_load(self):
        res = await self.locust_client.get("/stop")
        if res.status_code != httpx.codes.OK:
            logger.error(f"locust swarm failed: {res.status_code} {res.text}")
            raise Exception("Locust")

    async def slo_error(self, start_epoch, end_epoch) -> bool:
        '''Status of error SLO. Returns true if target SLO is satisfied.'''

        res = await self.metric_error_rate.query_range(start_epoch, end_epoch)
        if not res:
            logger.debug(f"{self.microservice_benchmark} no error rate data: {res}")
            return False
        errors = [float(val) for _, val in res[0]['values'] if float(val) > self.slo_error_rate]
        if len(errors) > 0:
            logger.debug(f"{self.microservice_benchmark} error rate exceeds slo {self.slo_error_rate} between [{start_epoch}; {end_epoch}]")
            return False
        return True

    async def restarted_pods(self, start_epoch, end_epoch) -> set[str]:
        restarted_pods = set()
        res = await self.metric_container_restarts.query_range(start_epoch, end_epoch)
        if not res:
            return restarted_pods

        for pod in res:
            for _timestamp, value in pod["values"]:
                if int(value) > 0:
                    restarted_pods.add(pod["metric"]["pod"])
        return restarted_pods

    async def slo_latency(self, start_epoch, end_epoch):
        """Status of latency SLO.

        The latency service level objective (SLO) depends on the application's
        current baseline. If there is a statistically significant increase in latency for
        the parameterized period [start_epoch; end_epoch], this function will return
        False, meaning that the latency SLO is not within target.

        """

        if not self.baseline_latency:
            # We don't have a frame of reference, and therefore the SLO is True by default
            return True

        res = await self.metric_latency.query_range(start_epoch, end_epoch)
        if not res:
            logger.debug(f"{self.microservice_benchmark} no container restarts data")
            return False

        compare_latency = [float(val) for _, val in res[0]['values']]
        has_effect = stats.has_effect(self.baseline_latency, compare_latency)
        relative_latency = np.median(compare_latency) / np.median(self.baseline_latency)
        logger.debug(f"{self.microservice_benchmark} has_effect={has_effect} relative_latency={relative_latency}")
        return not (has_effect and (relative_latency > 2))

    async def stable(self, start_epoch, end_epoch) -> bool:
        return (
            (await self.slo_error(start_epoch, end_epoch))
            and (len(await self.restarted_pods(start_epoch, end_epoch)) == 0)
        )

    async def set_baseline_latency(self, start_epoch, end_epoch) -> bool:
        logger.debug(f"{self.microservice_benchmark}: creating new latency baseline")
        res = await self.metric_latency.query_range(start_epoch, end_epoch)
        if not res:
            logger.debug(f"{self.microservice_benchmark} no latency data")
            return False
        latencies = res[0]['values']
        if len(latencies) < (end_epoch-start_epoch):
            logger.debug(f"not enough samples for baseline latency: {len(latencies)} < {end_epoch-start_epoch}")
            return False

        latencies = [float(val) for _, val in latencies]
        self.baseline_latency = latencies
        logger.debug(f"{self.microservice_benchmark}: created new latency baseline")
        return True
