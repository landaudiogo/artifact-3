from uuid import uuid4
from dataclasses import dataclass
from httpx import Client

import logging
import httpx

from .. import FaultTrait

logger = logging.getLogger(__name__)


@dataclass
class CPUStressParameters:
    uid: str
    node: str


class CPUStress(FaultTrait):


    def __init__(self, spec):
        self.fault = CPUStressParameters(
            node=spec["node"],
            uid=str(uuid4()),
        )

    def prepare(self):
        pass

    def execute(self):
        logger.debug(f"inject {self.fault}")
        chaosd = Client(base_url=f"http://{self.fault.node}:31767", timeout=10.0)

        data = {
            "uid": self.fault.uid,
            "attackCmd": f"host-cpu-stress attack",
            "recoverCmd": f"host-cpu-stress recover",
        }

        logger.debug(f"chaosd request: {chaosd.base_url}/api/attack/user_defined {data}")
        res = chaosd.post("/api/attack/user_defined", json=data)
        if res.status_code != httpx.codes.OK:
            logger.warn(f"chaosd request failed: {self.fault.uid}")
            logger.debug(f"status code: {res.status_code} {res.text}")
            raise Exception("Chaosd")
        logger.info(f"started host cpu stress {self.fault.uid}")

    def recover(self):
        logger.debug(f"recover {self.fault}")
        chaosd = Client(base_url=f"http://{self.fault.node}:31767", timeout=10.0)

        res = chaosd.delete(f"/api/attack/{self.fault.uid}")
        if res.status_code != httpx.codes.OK:
            logger.error(f"chaosd request failed: {res.status_code} {res.text}")
            raise Exception("Chaosd")
        logger.info(f"recovered host cpu stress {self.fault.uid}")
