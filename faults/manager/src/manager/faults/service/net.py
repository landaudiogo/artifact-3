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

logger = logging.getLogger(__name__)

NETWORK_BANDWIDTH_TEMPLATE = Template("""
    sum (
        rate(
            container_network_transmit_bytes_total{namespace="{{namespace}}", pod="{{pod}}"}[5m]
        ) * 8
    ) by (namespace, pod)
""")

CHAOSMESH_NETPARTITION_TEMPLATE = Template('''
    apiVersion: chaos-mesh.org/v1alpha1
    kind: NetworkChaos
    metadata:
      name: {{ name }}
    spec:
      action: partition
      mode: all
      selector:
        namespaces:
          - {{ namespace }}
        labelSelectors: {}
      direction: from
      externalTargets:
        - "10.0.0.0/8"
''')


CHAOSMESH_NETBANDWIDTH_TEMPLATE = Template('''
    apiVersion: chaos-mesh.org/v1alpha1
    kind: NetworkChaos
    metadata:
      name: {{ name }}
    spec:
      action: netem
      mode: all
      selector:
        pods: {}
      rate:
        rate: '{{ rate }}'
''')


class NetworkPartition:


    def __init__(self, kubernetes_client, spec):
        self.kubernetes_client = kubernetes_client
        self.spec = spec
        self.uuid = str(uuid4())

    def prepare(self):
        pass

    def execute(self):
        body = yaml.load(
            CHAOSMESH_NETPARTITION_TEMPLATE.render(
                name=self.uuid, 
                namespace=self.spec["namespace"], 
            ), 
            Loader=SafeLoader,
        )
        idx = self.spec["label_selector"].find("=")
        label_key, label_value = self.spec["label_selector"][:idx], self.spec["label_selector"][idx+1:]
        body["spec"]["selector"]["labelSelectors"][label_key] = label_value
        logger.debug(f"{body}")
        self.kubernetes_client.create_namespaced_custom_object(
            group="chaos-mesh.org",
            version="v1alpha1",
            namespace="faults",
            plural="networkchaos",
            body=body,
        )
        logger.info(f"execute network partition: namespace={self.spec['namespace']} label_selector={self.spec['label_selector']}")
        

    def recover(self):
        self.kubernetes_client.delete_namespaced_custom_object(
            group="chaos-mesh.org",
            version="v1alpha1",
            namespace="faults",
            plural="networkchaos",
            name=self.uuid,
        )
        logger.info(f"recover network partition: namespace={self.spec['namespace']} label_selector={self.spec['label_selector']}")


@dataclass
class NetworkBandwidthParameters:
    uid: str
    namespace: str
    pod: str 
    rate: str


class NetworkBandwidth:


    def __init__(self, core_k8s_client, custom_k8s_client, prometheus_client, spec):
        self.core_k8s_client = core_k8s_client
        self.custom_k8s_client = custom_k8s_client
        self.prometheus_client = prometheus_client
        self.spec = spec

        # prepare attributes
        self.fault_parameters = []


    def prepare(self):
        now = time.time()

        res = self.core_k8s_client.list_namespaced_pod(self.spec["namespace"], label_selector=self.spec["label_selector"])
        for pod in res.items:
            logger.debug(NETWORK_BANDWIDTH_TEMPLATE.render(namespace=pod.metadata.namespace, pod=pod.metadata.name))
            res = self.prometheus_client.get(
                "/api/v1/query",
                params={
                    "query": NETWORK_BANDWIDTH_TEMPLATE.render(namespace=pod.metadata.namespace, pod=pod.metadata.name),
                    "time": now
                }
            )

            if res.status_code != httpx.codes.OK:
                logger.error(f"prometheus query failed: {res.status_code} {res.text}")
                raise Exception("Prometheus")

            res = json.loads(res.text)
            logger.debug(res)
            for container in res["data"]["result"]:
                namespace, pod = container["metric"]["namespace"], container["metric"]["pod"]
                value = float(container["value"][1])
                logger.debug(f"{namespace} {pod} {value}")
                self.fault_parameters.append(
                    NetworkBandwidthParameters(
                        uid=str(uuid4()), 
                        namespace=namespace,
                        pod=pod,
                        rate=str(int((2/3)*value)) + 'bit',
                    )
                )

    def execute(self):
        for fault in self.fault_parameters:
            body = yaml.load(
                CHAOSMESH_NETBANDWIDTH_TEMPLATE.render(
                    name=fault.uid, 
                    rate=fault.rate
                ), 
                Loader=SafeLoader,
            )
            body["spec"]["selector"]["pods"][fault.namespace] = [fault.pod]
            logger.debug(f"{body}")
            self.custom_k8s_client.create_namespaced_custom_object(
                group="chaos-mesh.org",
                version="v1alpha1",
                namespace="faults",
                plural="networkchaos",
                body=body,
            )
            logger.info(f"execute network bandwidth limit: {fault}")
            

    def recover(self):
        for fault in self.fault_parameters:
            self.custom_k8s_client.delete_namespaced_custom_object(
                group="chaos-mesh.org",
                version="v1alpha1",
                namespace="faults",
                plural="networkchaos",
                name=fault.uid,
            )
            logger.info(f"recover network partition: namespace={fault} label_selector={fault}")
