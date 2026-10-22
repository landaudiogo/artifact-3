from jinja2 import Template
from httpx import Client
from uuid import uuid4
from dataclasses import dataclass
from yaml import SafeLoader

import yaml
import time
import json
import httpx
import logging

from .. import ExpectedRestarts, FaultTrait, NamespaceRestart

logger = logging.getLogger(__name__)

# This query calculates the 5 minute average Memory usage for a particular pod
MEMORY_TEMPLATE = Template("""
    sum (
        container_memory_working_set_bytes{
            # filter out empty and pause images
            image!~"|docker.io/library/pause.*",
            pod="{{pod}}",
            namespace="{{namespace}}",
        }
    ) by (node, id)
""")

CHAOSMESH_MEMSTRESS_TEMPLATE = Template('''
    kind: StressChaos
    apiVersion: chaos-mesh.org/v1alpha1
    metadata:
      name: {{ name }}
    spec:
      selector:
        namespaces:
          - {{ namespace }}
        labelSelectors: {}
      mode: all
      stressors:
        memory:
          workers: 10
          size: 10%
''')


class MemoryStress(FaultTrait):


    def __init__(self, kubernetes_client, spec):
        self.kubernetes_client = kubernetes_client
        self.spec = spec
        self.uuid = str(uuid4())

    def expected_restarts(self) -> ExpectedRestarts:
        return NamespaceRestart(self.spec["namespace"])

    def prepare(self):
        pass

    def execute(self):
        body = yaml.load(
            CHAOSMESH_MEMSTRESS_TEMPLATE.render(
                name=self.uuid, 
                namespace=self.spec["namespace"], 
            ), 
            Loader=SafeLoader,
        )
        idx = self.spec["label_selector"].find("=")
        label_key, label_value = self.spec["label_selector"][:idx], self.spec["label_selector"][idx+1:]
        body["spec"]["selector"]["labelSelectors"][label_key] = label_value
        self.kubernetes_client.create_namespaced_custom_object(
            group="chaos-mesh.org",
            version="v1alpha1",
            namespace="faults",
            plural="stresschaos",
            body=body,
        )
        logger.info(f"execute memory stress: namespace={self.spec['namespace']} label_selector={self.spec['label_selector']}")
        

    def recover(self):
        self.kubernetes_client.delete_namespaced_custom_object(
            group="chaos-mesh.org",
            version="v1alpha1",
            namespace="faults",
            plural="stresschaos",
            name=self.uuid,
        )
        logger.info(f"recover memory stress: namespace={self.spec['namespace']} label_selector={self.spec['label_selector']}")

@dataclass
class MemoryFaultParameters:
    uid: str
    node: str
    cgroup: str
    memory_max: int


class MemoryReduce(FaultTrait):


    def __init__(self, kubernetes_client, prometheus_client, node_chaosd_map: dict[str, Client], spec):
        self.kubernetes_client = kubernetes_client
        self.prometheus_client = prometheus_client
        self.node_chaosd_map = node_chaosd_map
        self.spec = spec

        # prepare attributes
        self.fault_parameters = [] 

    def expected_restarts(self) -> ExpectedRestarts:
        return NamespaceRestart(self.spec["namespace"])

    def prepare(self):
        now = time.time()

        res = self.kubernetes_client.list_namespaced_pod(self.spec["namespace"], label_selector=self.spec["label_selector"])
        for pod in res.items:
            logger.debug(MEMORY_TEMPLATE.render(namespace=pod.metadata.namespace, pod=pod.metadata.name))
            res = self.prometheus_client.get(
                "/api/v1/query",
                params={
                    "query": MEMORY_TEMPLATE.render(namespace=pod.metadata.namespace, pod=pod.metadata.name),
                    "time": now
                }
            )

            if res.status_code != httpx.codes.OK:
                logger.error(f"prometheus query failed: {res.status_code} {res.text}")
                raise Exception("Prometheus")

            res = json.loads(res.text)
            logger.debug(res)
            for container in res["data"]["result"]:
                node, id = container["metric"]["node"], container["metric"]["id"]
                value = int(container["value"][1])
                logger.debug(f"{node} {id} {value}")
                self.fault_parameters.append(
                    MemoryFaultParameters(
                        uid=str(uuid4()), 
                        node=node,
                        cgroup=id,
                        memory_max=int((1/3)*value)
                    )
                )

    def execute(self):
        faults = self.fault_parameters
        self.fault_parameters = []
        for fault in faults:
            logger.debug(f"inject {fault}")
            chaosd = self.node_chaosd_map.get(fault.node)
            if chaosd is None:
                raise Exception(f"Missing node chaosd entry for `{fault.node}`")

            data = {
                "uid": fault.uid,
                "attackCmd": f"service-memory-reduce attack --uid {fault.uid} --cgroup {fault.cgroup} --memory-max {fault.memory_max}",
                "recoverCmd": f"service-memory-reduce recover --uid {fault.uid}",
            }

            logger.debug(f"chaosd request: {chaosd.base_url}/api/attack/user_defined {data}")
            res = chaosd.post("/api/attack/user_defined", json=data)
            if res.status_code != httpx.codes.OK:
                logger.warn(f"chaosd request failed: {fault.uid}")
                logger.debug(f"status code: {res.status_code} {res.text}")
                continue
            self.fault_parameters.append(fault)
            logger.info(f"started memory reduce {fault.uid}")

    def recover(self):
        for fault in self.fault_parameters:
            logger.debug(f"recover {fault}")
            chaosd = self.node_chaosd_map.get(fault.node)
            if chaosd is None:
                raise Exception(f"Missing node chaosd entry for `{fault.node}`")

            res = chaosd.delete(f"/api/attack/{fault.uid}")
            if res.status_code != httpx.codes.OK:
                logger.error(f"chaosd request failed: {res.status_code} {res.text}")
                raise Exception("Chaosd")
            logger.info(f"recovered memory reduce {fault.uid}")
