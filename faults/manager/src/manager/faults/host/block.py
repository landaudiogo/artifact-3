from uuid import uuid4
from dataclasses import dataclass
from httpx import Client

import logging
import httpx

from .. import FaultTrait

logger = logging.getLogger(__name__)


@dataclass
class BlockLatencyParameters:
    uid: str
    node: str


class BlockLatency(FaultTrait):


    def __init__(self, node_chaosd_map: dict[str, Client], spec):
        self.fault = BlockLatencyParameters(
            node=spec["node"],
            uid=str(uuid4()),
        )
        self.chaosd = node_chaosd_map[spec["node"]]

    def prepare(self):
        pass

    def execute(self):
        logger.debug(f"inject {self.fault}")

        data = {
            "uid": self.fault.uid,
            "attackCmd": f"host-block-latency attack",
            "recoverCmd": f"host-block-latency recover",
        }

        logger.debug(f"chaosd request: {self.chaosd.base_url}/api/attack/user_defined {data}")
        res = self.chaosd.post("/api/attack/user_defined", json=data)
        if res.status_code != httpx.codes.OK:
            logger.warning(f"chaosd request failed: {self.fault.uid}")
            logger.debug(f"status code: {res.status_code} {res.text}")
            raise Exception("Chaosd")
        logger.info(f"started host block latency {self.fault.uid}")

    def recover(self):
        logger.debug(f"recover {self.fault}")

        res = self.chaosd.delete(f"/api/attack/{self.fault.uid}")
        if res.status_code != httpx.codes.OK:
            logger.error(f"chaosd request failed: {res.status_code} {res.text}")
            raise Exception("Chaosd")
        logger.info(f"recovered host block latency {self.fault.uid}")
