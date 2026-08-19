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

@dataclass
class NetworkPartitionParameters:
    uid: str
    node: str
    destination_address: str
    device: str

class NetworkPartition:


    def __init__(self, kubernetes_client, spec):
        self.kubernetes_client = kubernetes_client
        self.fault = NetworkPartitionParameters(
            uid=str(uuid4()),
            node=spec["node"],
            destination_address=spec["destination_address"],
            device=spec["device"],
        )

    def prepare(self):
        pass

    def execute(self):
        body = yaml.load(
            CHAOSMESH_NETPARTITION_TEMPLATE.render(
                uid=self.fault.uid, 
                node=self.fault.node, 
                destination_address=self.fault.destination_address, 
                device=self.fault.device, 
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
        logger.info(f"execute host network partition: {self.fault}")
        
    def recover(self):
        self.kubernetes_client.delete_namespaced_custom_object(
            group="chaos-mesh.org",
            version="v1alpha1",
            namespace="faults",
            plural="physicalmachinechaos",
            name=self.fault.uid,
        )
        logger.info(f"recover host network partition: {self.fault}")
