import asyncio
import logging
import subprocess
import time
import httpx

from datetime import datetime, timedelta
from httpx import AsyncClient
from pathlib import Path

from ..kpis.prometheus import (
    PrometheusKPI,
    LOCUST_LATENCY_95_TEMPLATE,
    LOCUST_USERS_TEMPLATE,
    LOCUST_ERROR_RATE_TEMPLATE,
    CONTAINER_START_WINDOW_TEMPLATE,
)


logger = logging.getLogger(__name__)


class OnlineBoutique:


    def __init__(self, manifest_path: Path, locust_url: str, prometheus_client):
        self.manifest_path = manifest_path
        self.locust_client = AsyncClient(base_url=locust_url)
        self.latency = PrometheusKPI(prometheus_client, LOCUST_LATENCY_95_TEMPLATE.render(
            filter='{ service="locust-online-boutique" }'
        ))
        self.error_rate = PrometheusKPI(prometheus_client, LOCUST_ERROR_RATE_TEMPLATE.render(
            filter='{ service="locust-online-boutique" }'
        ))
        self.container_restarts = PrometheusKPI(prometheus_client, CONTAINER_START_WINDOW_TEMPLATE.render(
            filter='{ namespace="social-network" }'
        ))
        self.user_count = PrometheusKPI(prometheus_client, LOCUST_USERS_TEMPLATE.render(
            filter='{ service="locust-online-boutique" }'
        ))

    def deploy(self) -> bool:
        '''Creates the application's k8s resources. Returns `True` if it succeeds and `False` otherwise'''

        # This command is already asynchronous.
        # We do care if creating any of the kubernetes resources fails.
        logger.info("creating online boutique k8s resources")
        completed_process = subprocess.run(
            f"kubectl apply -f {self.manifest_path}",
            shell=True,
            check=False, # we don't want an exception to be raised non-zero exit code
            capture_output=True
        )
        if completed_process.returncode != 0:
            logger.warning(f"kubectl did not exit successfully: stdout[{completed_process.stdout}] stderr[{completed_process.stderr}]")
            return False
        logger.info("online boutique k8s resources created")
        return True


    async def wait_for_ready(self):
        logger.info("waiting for online boutique resources to be available")
        process = await asyncio.create_subprocess_exec(
            "kubectl", "wait", "--namespace=online-boutique", "deploy", "--all", "--for=condition=Available", "--timeout=120s",
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
            "kubectl", "wait", "--namespace=load-generators-online-boutique", "deploy", "--all", "--for=condition=Available", "--timeout=120s",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.wait()
        if process.returncode != 0:
            stdout = await process.stdout.read()
            stderr = await process.stderr.read()
            logger.warning(f"kubectl process did not exit successfully: stdout[{stdout}] stderr[{stderr}]")
            return False
        logger.info("online boutique resources are available")
        return True

    def destroy(self):
        '''Deletes the application's k8s resources. Returns `True` if it succeeds and `False` otherwise'''

        logger.info("deleting online boutique k8s resources")
        completed_process = subprocess.run(
            f"kubectl delete -f {self.manifest_path}",
            shell=True,
            check=False, # we don't want an exception to be raised on non-zero exit code
            capture_output=True
        )
        if completed_process.returncode != 0:
            logger.warning(f"kubectl did not exit successfully: stdout[{completed_process.stdout}] stderr[{completed_process.stderr}]")
            return False
        logger.info("online boutique k8s resources deleted")
        return True

    async def set_load(self, users: int, timeout: timedelta = timedelta(minutes=1)):
        end = datetime.now() + timeout
        logger.info(f"online boutique setting load to {users}")

        while datetime.now() < end:
            res = await self.locust_client.post(
                "/swarm",
                data={"user_count": users, "spawn_rate": 20}
            )

            if res.status_code != httpx.codes.OK:
                logger.error(f"locust swarm failed: {res.status_code} {res.text}")
                raise Exception("Locust")

            res = await self.user_count.query()
            if not res:
                continue

            current_users = int(res[0]["value"][1])
            if (current_users == users):
                logger.info(f"online boutique load set to {users}")
                return True

            logger.info(f"online boutique current load {current_users} != {users} desired. Retrying")
            await asyncio.sleep(10)

        logger.error(f"failed to set online boutique load to {users} users")
        return False


    async def stop_load(self):
        res = await self.locust_client.get("/stop")
        if res.status_code != httpx.codes.OK:
            logger.error(f"locust swarm failed: {res.status_code} {res.text}")
            raise Exception("Locust")
