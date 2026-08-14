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

NET_BANDWIDTH_TEMPLATE = Template("""
    sum (
        rate(
            container_network_transmit_bytes_total{namespace="{{namespace}}", pod="{{pod}}"}[1m]
        ) * 8
    ) by (pod)
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
