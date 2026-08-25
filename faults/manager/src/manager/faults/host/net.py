from jinja2 import Template
from httpx import Client
from uuid import uuid4
from dataclasses import dataclass
from yaml import SafeLoader
from pydantic import ByteSize, BaseModel

import yaml
import time
import json
import httpx
import logging
import socket

from .. import FaultTrait

logger = logging.getLogger(__name__)

CHAOSMESH_NETPARTITION_TEMPLATE = Template('''
    apiVersion: chaos-mesh.org/v1alpha1
    kind: PhysicalMachineChaos
    metadata:
      name: {{ uid }}
    spec:
      action: network-partition
      mode: one
      address:
        - http://{{ node }}:31767
      network-partition:
        ip-address: {{ destination_address }}
        device: {{ device }}
        direction: to
''')


CHAOSMESH_NETBANDWIDTH_TEMPLATE = Template('''
    apiVersion: chaos-mesh.org/v1alpha1
    kind: PhysicalMachineChaos
    metadata:
      name: {{ uid }}
    spec:
      action: network-bandwidth
      mode: one
      address:
        - http://{{ node }}:31767
      network-bandwidth:
        device: {{ device }}
        rate: {{ rate }}bps
        limit: {{ limit }}
        buffer: {{ buffer }}
''')

NETWORK_BANDWIDTH_TEMPLATE = Template("""
    rate(
        node_network_transmit_bytes_total{
            instance="{{ node_ip }}:9100", 
            device=~"en.*|wl.*",
            job="node-exporter",
        }[5m]
    ) * 8
""")


@dataclass
class NetworkPartitionParameters:
    uid: str
    node: str
    destination_address: str
    device: str

class NetworkPartition(FaultTrait):


    def __init__(self, kubernetes_client, prometheus_client, spec):
        self.kubernetes_client = kubernetes_client
        self.prometheus_client = prometheus_client
        self.spec = spec

        # prepare parameters
        self.fault_parameters = []

    def prepare(self):
        now = time.time()
        node_ip = socket.gethostbyname(self.spec["node"])
        query = NETWORK_BANDWIDTH_TEMPLATE.render(node_ip=node_ip)
        logger.debug(query)
        res = self.prometheus_client.get(
            "/api/v1/query",
            params={
                "query": query,
                "time": now
            }
        )

        if res.status_code != httpx.codes.OK:
            logger.error(f"prometheus query failed: {res.status_code} {res.text}")
            raise Exception("Prometheus")

        res = json.loads(res.text)

        for device_metric in res["data"]["result"]:
            device = device_metric["metric"]["device"]
            rate_bps = float(device_metric["value"][1])
            if rate_bps < 1e-6:
                continue

            logger.debug(f"{device}: {rate_bps} bps")
            self.fault_parameters.append(NetworkPartitionParameters(
                uid=str(uuid4()),
                node=self.spec["node"],
                destination_address=socket.gethostbyname(self.spec["destination_node"]),
                device=device,
            ))

    def execute(self):
        for fault in self.fault_parameters:
            body = yaml.load(
                CHAOSMESH_NETPARTITION_TEMPLATE.render(
                    uid=fault.uid, 
                    node=fault.node, 
                    destination_address=fault.destination_address, 
                    device=fault.device, 
                ), 
                Loader=SafeLoader,
            )

            logger.debug(f"{body}")
            self.kubernetes_client.create_namespaced_custom_object(
                group="chaos-mesh.org",
                version="v1alpha1",
                namespace="faults",
                plural="physicalmachinechaos",
                body=body,
            )
            logger.info(f"execute host network partition: {fault}")

    def recover(self):
        for fault in self.fault_parameters:
            self.kubernetes_client.delete_namespaced_custom_object(
                group="chaos-mesh.org",
                version="v1alpha1",
                namespace="faults",
                plural="physicalmachinechaos",
                name=fault.uid,
            )
            logger.info(f"recover host network partition: {fault}")

class NetworkBandwidthParameters(BaseModel):
    uid: str
    node: str
    device: str
    # The following parameters are documented [here](https://chaos-mesh.org/docs/simulate-network-chaos-in-physical-nodes/#simulate-network-bandwidth-using-the-service-mode)
    rate: ByteSize
    # The maximum amount of bytes that tokens can be available for instantaneously
    buffer: ByteSize
    # The number of bytes that can be queued waiting for tokens to become available
    limit: ByteSize

class NetworkBandwidth(FaultTrait):


    def __init__(self, custom_k8s_client, prometheus_client, spec):
        self.custom_k8s_client = custom_k8s_client
        self.prometheus_client = prometheus_client
        self.spec = spec

        # prepare attributes
        self.fault_parameters = []


    def prepare(self):
        node_ip = socket.gethostbyname(self.spec["node"])

        now = time.time()
        query = NETWORK_BANDWIDTH_TEMPLATE.render(
            node_ip=node_ip, 
        )
        logger.debug(query)
        res = self.prometheus_client.get(
            "/api/v1/query",
            params={
                "query": query,
                "time": now
            }
        )

        if res.status_code != httpx.codes.OK:
            logger.error(f"prometheus query failed: {res.status_code} {res.text}")
            raise Exception("Prometheus")

        res = json.loads(res.text)
        logger.debug(res)

        for device_metric in res["data"]["result"]:
            device = device_metric["metric"]["device"]
            rate = float(device_metric["value"][1])
            logger.debug(device)
            self.fault_parameters.append(
                NetworkBandwidthParameters(
                    uid=str(uuid4()), 
                    node=self.spec["node"],
                    device=device,
                    rate=int(rate*0.7),
                    buffer=self.spec["buffer"],
                    limit=self.spec["limit"],
                )
            )

    def execute(self):
        for fault in self.fault_parameters:
            logger.debug(fault)
            body = yaml.load(
                CHAOSMESH_NETBANDWIDTH_TEMPLATE.render(
                    uid=fault.uid, 
                    node=fault.node,
                    device=fault.device,
                    rate=fault.rate,
                    limit=fault.limit,
                    buffer=fault.buffer,
                ), 
                Loader=SafeLoader,
            )
            logger.debug(body)

            self.custom_k8s_client.create_namespaced_custom_object(
                group="chaos-mesh.org",
                version="v1alpha1",
                namespace="faults",
                plural="physicalmachinechaos",
                body=body,
            )
            logger.info(f"execute host network bandwidth limit: {fault}")


    def recover(self):
        for fault in self.fault_parameters:
            self.custom_k8s_client.delete_namespaced_custom_object(
                group="chaos-mesh.org",
                version="v1alpha1",
                namespace="faults",
                plural="physicalmachinechaos",
                name=fault.uid,
            )
            logger.info(f"recover host network partition: {fault}")
