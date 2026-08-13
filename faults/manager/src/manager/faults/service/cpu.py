from jinja2 import Template
from httpx import Client
from uuid import uuid4
from dataclasses import dataclass

import time
import json
import httpx
import logging

logger = logging.getLogger(__name__)

# This query calculates the 5 minute average CPU usage for a particular pod
CPU_TEMPLATE = Template("""
    sum by (node, id) (
        rate(container_cpu_usage_seconds_total{
            image!="",
            namespace="{{namespace}}",
            pod="{{pod}}",
        }[5m])
    )
""")

@dataclass
class CPUParameters:
    uid: str
    node: str
    cgroup: str
    cpu_max: int


class CPUStress:


    def __init__(self, kubernetes_client, prometheus_client, spec):
        self.kubernetes_client = kubernetes_client
        self.prometheus_client = prometheus_client
        self.spec = spec

        # prepare attributes
        self.fault_parameters = [] 

    def prepare(self):
        now = time.time()

        res = self.kubernetes_client.list_namespaced_pod(self.spec["namespace"], label_selector=self.spec["label_selector"])
        for pod in res.items:
            logger.debug(pod.metadata.name)
            logger.debug(CPU_TEMPLATE.render(namespace=pod.metadata.namespace, pod=pod.metadata.name))
            res = self.prometheus_client.get(
                "/api/v1/query",
                params={
                    "query": CPU_TEMPLATE.render(namespace=pod.metadata.namespace, pod=pod.metadata.name),
                    "time": now
                }
            )

            if res.status_code != httpx.codes.OK:
                logger.error(f"prometheus query failed: {res.code} {res.text}")
                raise Exception("Prometheus")

            res = json.loads(res.text)
            for container in res["data"]["result"]:
                value = float(container["value"][1])
                if value < 1e-6:
                    continue

                # A cgroup's cpu.max file has two integer values `x*y y`.
                # In this example, y is the period (in microseconds), and is a
                # value between 0 and 1. As such, if we write `3000 100000`, we
                # are limiting the cgroup to using only 3% of a core, or in
                # other words 30m CPUs
                # 
                # Therefore, given that prometheus returns a value in the
                # following format: 
                # 0.03973912709853217, 
                # where 1 represents 1000m CPUs (or 1 CPU), we can convert it
                # into the appropriate format with value*100_000. We add an
                # additional 5% to what prometheus reported for some additional
                # headroom.
                value = int(value * 100_000)
                node, id = container["metric"]["node"], container["metric"]["id"]
                logger.debug(f"{node} {id}: {value}")
                self.fault_parameters.append(CPUParameters(uid=str(uuid4()), node=node, cgroup=id, cpu_max=int(value*1.05)))

    def execute(self):
        node_chaosd = {}
        
        for fault in self.fault_parameters:
            logger.debug(f"Executing {fault}")
            if node_chaosd.get(fault.node) is None:
                node_chaosd[fault.node] = Client(base_url=f"http://{fault.node}:31767")

            chaosd = node_chaosd[fault.node]
            data = {
                "uid": fault.uid,
                "attackCmd": f"service-cpu-stress attack --uid {fault.uid} --cgroup {fault.cgroup} --cpu-max {fault.cpu_max}",
                "recoverCmd": f"service-cpu-stress recover --uid {fault.uid}",
            }
            
            logger.debug(f"chaosd request:\n{chaosd.base_url}/api/attack/user_defined\n{data}")
            res = chaosd.post("/api/attack/user_defined", json=data)
            if res.status_code != httpx.codes.OK:
                logger.error(f"chaosd request error: {res.status_code} {res.text}")
                raise Exception("Chaosd")

    def recover(self):
        node_chaosd = {}
        
        for fault in self.fault_parameters:
            logger.debug(f"Recovering {fault}")
            if node_chaosd.get(fault.node) is None:
                node_chaosd[fault.node] = Client(base_url=f"http://{fault.node}:31767")

            chaosd = node_chaosd[fault.node]
            res = chaosd.delete(f"/api/attack/{fault.uid}")
            if res.status_code != httpx.codes.OK:
                logger.error(f"chaosd request error: {res.status_code} {res.text}")
                raise Exception("Chaosd")
            logger.debug(f"Successfully recovered from fault with uid {fault.uid}")


class CPUReduce:


    def __init__(self, kubernetes_client, prometheus_client, spec):
        self.kubernetes_client = kubernetes_client
        self.prometheus_client = prometheus_client
        self.spec = spec

        # prepare attributes
        self.fault_parameters = [] 

    def prepare(self):
        now = time.time()

        res = self.kubernetes_client.list_namespaced_pod(self.spec["namespace"], label_selector=self.spec["label_selector"])
        for pod in res.items:
            logger.debug(pod.metadata.name)
            logger.debug(CPU_TEMPLATE.render(namespace=pod.metadata.namespace, pod=pod.metadata.name))
            res = self.prometheus_client.get(
                "/api/v1/query",
                params={
                    "query": CPU_TEMPLATE.render(namespace=pod.metadata.namespace, pod=pod.metadata.name),
                    "time": now
                }
            )

            if res.status_code != httpx.codes.OK:
                logger.error(f"prometheus query failed: {res.code} {res.text}")
                raise Exception("Prometheus")

            res = json.loads(res.text)
            for container in res["data"]["result"]:
                value = float(container["value"][1])
                if value < 1e-6:
                    continue

                # A cgroup's cpu.max file has two integer values `x*y y`.
                # In this example, y is the period (in microseconds), and is a
                # value between 0 and 1. As such, if we write `3000 100000`, we
                # are limiting the cgroup to using only 3% of a core, or in
                # other words 30m CPUs
                # 
                # Therefore, given that prometheus returns a value in the
                # following format: 
                # 0.03973912709853217, 
                # where 1 represents 1000m CPUs (or 1 CPU), we can convert it
                # into the appropriate format with value*100_000. We add an
                # additional 5% to what prometheus reported for some additional
                # headroom.
                value = int(value * 100_000)
                node, id = container["metric"]["node"], container["metric"]["id"]
                logger.debug(f"{node} {id}: {value}")
                self.fault_parameters.append(CPUParameters(uid=str(uuid4()), node=node, cgroup=id, cpu_max=int(value*0.5)))

    def execute(self):
        node_chaosd = {}
        
        for fault in self.fault_parameters:
            logger.debug(f"Executing {fault}")
            if node_chaosd.get(fault.node) is None:
                node_chaosd[fault.node] = Client(base_url=f"http://{fault.node}:31767")

            chaosd = node_chaosd[fault.node]
            data = {
                "uid": fault.uid,
                "attackCmd": f"service-cpu-reduce attack --uid {fault.uid} --cgroup {fault.cgroup} --cpu-max {fault.cpu_max}",
                "recoverCmd": f"service-cpu-reduce recover --uid {fault.uid}",
            }
            
            logger.debug(f"chaosd request:\n{chaosd.base_url}/api/attack/user_defined\n{data}")
            res = chaosd.post("/api/attack/user_defined", json=data)
            if res.status_code != httpx.codes.OK:
                logger.error(f"chaosd request error: {res.status_code} {res.text}")
                raise Exception("Chaosd")

    def recover(self):
        node_chaosd = {}
        
        for fault in self.fault_parameters:
            logger.debug(f"Recovering {fault}")
            if node_chaosd.get(fault.node) is None:
                node_chaosd[fault.node] = Client(base_url=f"http://{fault.node}:31767")

            chaosd = node_chaosd[fault.node]
            res = chaosd.delete(f"/api/attack/{fault.uid}")
            if res.status_code != httpx.codes.OK:
                logger.error(f"chaosd request error: {res.status_code} {res.text}")
                raise Exception("Chaosd")
            logger.debug(f"Successfully recovered from fault with uid {fault.uid}")
