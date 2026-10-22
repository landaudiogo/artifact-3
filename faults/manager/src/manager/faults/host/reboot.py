from uuid import uuid4
from dataclasses import dataclass
from httpx import Client
from datetime import timedelta, datetime

import logging
import httpx
import time

from httpx_retries import Retry, RetryTransport

from .. import ExpectedRestarts, FaultTrait, HostRestart

logger = logging.getLogger(__name__)


@dataclass
class RebootParameters:
    uid: str
    node: str


class Reboot(FaultTrait):


    def __init__(self, node_chaosd_map: dict[str, Client], spec):
        self.fault = RebootParameters(
            uid=str(uuid4()),
            node=spec["node"],
        )
        retry = Retry(total=5, backoff_factor=2, max_backoff_wait=5)
        transport = RetryTransport(retry=retry)
        self.node_chaosd_map = node_chaosd_map

        # This fault type depends on the client timing out to ensure that the
        # node is down and to check whether it is up. As such we cannot use
        # the clients passed as an argument since they have very permissive
        # timeout and retry policies.
        self.chaosd = Client(base_url=node_chaosd_map[spec["node"]].base_url, transport=transport)

    def expected_restarts(self) -> ExpectedRestarts:
        return HostRestart()

    def prepare(self):
        pass

    def execute(self):
        logger.debug(f"inject {self.fault}")

        data = {
            "uid": self.fault.uid,
            "attackCmd": f"systemctl reboot",
            "recoverCmd": f"echo no-op",
        }

        logger.debug(f"chaosd request: {self.chaosd.base_url}/api/attack/user_defined {data}")
        res = self.chaosd.post("/api/attack/user_defined", json=data)
        if res.status_code != httpx.codes.OK:
            logger.warning(f"chaosd request failed: {self.fault.uid}")
            logger.debug(f"status code: {res.status_code} {res.text}")
            raise Exception("Chaosd")
        logger.info(f"started host reboot: {self.fault}")
        self._wait_for_node_down(timedelta(minutes=1))

    def recover(self):
        self._wait_for_node_up(timedelta(minutes=10))
        logger.debug(f"recover {self.fault}")

        res = self.chaosd.delete(f"/api/attack/{self.fault.uid}")
        if res.status_code != httpx.codes.OK:
            logger.error(f"chaosd request failed: {res.status_code} {res.text}")
            raise Exception("Chaosd")
        logger.info(f"recovered host reboot: {self.fault}")

    def _wait_for_node_up(self, deadline: timedelta):
        logger.info(f"waiting for node {self.fault.node} up")
        end = datetime.now() + deadline
        while datetime.now() < end:
            try:
                res = self.chaosd.get("/api/system/health")
                if res.status_code == httpx.codes.OK:
                    logger.debug(f"node {self.fault.node} is up")
                    return
            except Exception as e:
                pass
            
            time.sleep(5)

        raise Exception(f"Node {self.fault.node} not ready within {deadline} deadline")

    def _wait_for_node_down(self, deadline: timedelta):
        logger.info(f"waiting for node {self.fault.node} down")
        end = datetime.now() + deadline
        while datetime.now() < end:
            try:
                res = self.chaosd.get("/api/system/health", timeout=1)
                if res.status_code == httpx.codes.OK:
                    logger.debug(f"node {self.fault.node} is still up")
            except Exception as e:
                logger.info(f"chaosd instance {self.chaosd.base_url} down")
                logger.debug(f"reason: {e}")
                return
            time.sleep(5)

        raise Exception(f"Node {self.fault.node} stayed up until {deadline} deadline")
