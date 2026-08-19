from uuid import uuid4
from dataclasses import dataclass
from httpx import Client

import logging
import httpx

logger = logging.getLogger(__name__)


@dataclass
class BlockLatencyParameters:
    uid: str
    node: str
    pod_uid: str


class BlockLatency:


    def __init__(self, kubernetes_client, spec):
        self.kubernetes_client = kubernetes_client
        self.spec = spec

        # prepare parameters
        self.fault_parameters = []

    def prepare(self):
        res = self.kubernetes_client.list_namespaced_pod(self.spec["namespace"], label_selector=self.spec["label_selector"])
        for pod in res.items:
            self.fault_parameters.append(
                BlockLatencyParameters(
                    node=pod.spec.node_name, 
                    pod_uid=pod.metadata.uid, 
                    uid=str(uuid4()),
                )
            )
    
    def execute(self):
        node_chaosd = {}

        faults = self.fault_parameters
        self.fault_parameters = []
        for fault in faults:
            logger.debug(f"inject {fault}")
            if node_chaosd.get(fault.node) is None:
                node_chaosd[fault.node] = Client(base_url=f"http://{fault.node}:31767", timeout=10.0)

            chaosd = node_chaosd[fault.node]
            data = {
                "uid": fault.uid,
                "attackCmd": f"service-block-latency attack {fault.pod_uid}",
                "recoverCmd": f"service-block-latency recover {fault.pod_uid}",
            }

            logger.debug(f"chaosd request: {chaosd.base_url}/api/attack/user_defined {data}")
            res = chaosd.post("/api/attack/user_defined", json=data)
            if res.status_code != httpx.codes.OK:
                logger.warn(f"chaosd request failed: {fault.uid}")
                logger.debug(f"status code: {res.status_code} {res.text}")
                continue
            self.fault_parameters.append(fault)
            logger.info(f"started block latency {fault.uid}")

    def recover(self):
        node_chaosd = {}
        
        for fault in self.fault_parameters:
            logger.debug(f"recover {fault}")
            if node_chaosd.get(fault.node) is None:
                node_chaosd[fault.node] = Client(base_url=f"http://{fault.node}:31767", timeout=10.0)

            chaosd = node_chaosd[fault.node]
            res = chaosd.delete(f"/api/attack/{fault.uid}")
            if res.status_code != httpx.codes.OK:
                logger.error(f"chaosd request failed: {res.status_code} {res.text}")
                raise Exception("Chaosd")
            logger.info(f"recovered block latency {fault.uid}")
