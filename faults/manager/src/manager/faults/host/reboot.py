from uuid import uuid4
from dataclasses import dataclass
from httpx import Client
from datetime import timedelta, datetime

import logging
import httpx
import time

from .. import FaultTrait

logger = logging.getLogger(__name__)


@dataclass
class RebootParameters:
    uid: str
    node: str


class Reboot(FaultTrait):


    def __init__(self, spec):
        self.fault = RebootParameters(
            uid=str(uuid4()),
            node=spec["node"],
        )

    def prepare(self):
        pass

    def execute(self):
        logger.debug(f"inject {self.fault}")
        chaosd = Client(base_url=f"http://{self.fault.node}:31767", timeout=10.0)

        data = {
            "uid": self.fault.uid,
            "attackCmd": f"systemctl reboot",
            "recoverCmd": f"echo no-op",
        }

        logger.debug(f"chaosd request: {chaosd.base_url}/api/attack/user_defined {data}")
        res = chaosd.post("/api/attack/user_defined", json=data)
        if res.status_code != httpx.codes.OK:
            logger.warn(f"chaosd request failed: {self.fault.uid}")
            logger.debug(f"status code: {res.status_code} {res.text}")
            raise Exception("Chaosd")
        logger.info(f"started host reboot: {self.fault}")
        self._wait_for_node_down(timedelta(minutes=1))

    def recover(self):
        self._wait_for_node_up(timedelta(minutes=10))
        logger.debug(f"recover {self.fault}")
        chaosd = Client(base_url=f"http://{self.fault.node}:31767", timeout=10.0)

        res = chaosd.delete(f"/api/attack/{self.fault.uid}")
        if res.status_code != httpx.codes.OK:
            logger.error(f"chaosd request failed: {res.status_code} {res.text}")
            raise Exception("Chaosd")
        logger.info(f"recovered host reboot: {self.fault}")

    def _wait_for_node_up(self, deadline: timedelta):
        logger.info(f"waiting for node {self.fault.node} ready")
        end = datetime.now() + deadline
        while datetime.now() < end:
            try:
                chaosd = Client(base_url=f"http://{self.fault.node}:31767", timeout=10.0)
                res = chaosd.get("/api/system/health")
                if res.status_code == httpx.codes.OK:
                    logger.info(f"node {self.fault.node} ready")
                    return
            except Exception as e:
                pass
            
            time.sleep(5)

        raise Exception(f"Node {self.fault.node} not ready within {deadline} deadline")

    def _wait_for_node_down(self, deadline: timedelta):
        logger.info(f"waiting for node {self.fault.node} ready")
        end = datetime.now() + deadline
        while datetime.now() < end:
            try:
                chaosd = Client(base_url=f"http://{self.fault.node}:31767", timeout=10.0)
                res = chaosd.get("/api/system/health")
                if res.status_code == httpx.codes.OK:
                    logger.info(f"node {self.fault.node} ready")
                    continue
            except Exception as e:
                logger.info(f"chaosd instance {chaosd.base_url} down")
                logger.debug(f"reason: {e}")
                return
            
            time.sleep(5)

        raise Exception(f"Node {self.fault.node} stayed up until {deadline} deadline")
