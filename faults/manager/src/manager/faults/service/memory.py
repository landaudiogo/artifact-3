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

# This query calculates the 5 minute average Memory usage for a particular pod
MEMORY_TEMPLATE = Template("""
    sum by (namespace,pod)(container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",image!="",namespace=~"online-boutique|social-network"})
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


@dataclass
class MemoryParameters:
    uid: str
    node: str
    cgroup: str

class MemoryStress:


    def __init__(self, kubernetes_client, spec):
        self.kubernetes_client = kubernetes_client
        self.spec = spec
        self.uuid = str(uuid4())

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


class MemoryReduce:
    pass
