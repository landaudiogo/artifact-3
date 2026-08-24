from jinja2 import Template
from httpx import Client
from uuid import uuid4
from dataclasses import dataclass
from yaml import SafeLoader
from typing import Optional

import yaml
import time
import json
import httpx
import logging

logger = logging.getLogger(__name__)

FAULT_POD_TEMPLATE = Template('''
    apiVersion: v1
    kind: Pod
    metadata:
      name: {{ name }}
    spec:
      containers:
      - image: dclandau/mongodb-fault:latest
        name: mongodb-fsync-lock
        args:
        - "--host"
        - "{{ host }}"
        - "--port"
        - "{{ port }}"
        - "--lock-duration"
        - "{{ lock_duration }}"
        - "--interval"
        - "{{ interval }}"
''')


@dataclass
class MongodbFsyncLockParameters:
    uid: str
    host: str 
    port: str 
    user: Optional[str]
    password: Optional[str]
    lock_duration: str 
    interval: str 


class MongodbFsyncLock:


    def __init__(self, kubernetes_client, spec):
        self.kubernetes_client = kubernetes_client
        self.fault = MongodbFsyncLockParameters(
            uid=str(uuid4()),
            host=spec["host"],
            port=spec["port"],
            user=spec.get("user"),
            password=spec.get("password"),
            lock_duration=spec["lock_duration"],
            interval=spec["interval"],
        )

    def prepare(self):
        pass

    def execute(self):
        body = yaml.load(
            FAULT_POD_TEMPLATE.render(
                name=self.fault.uid, 
                host=self.fault.host,
                port=self.fault.port,
                lock_duration=self.fault.lock_duration,
                interval=self.fault.interval,
            ),
            Loader=SafeLoader,
        )
        if self.fault.user is not None:
            body["spec"]["containers"][0]["args"].append("--user")
            body["spec"]["containers"][0]["args"].append(f"{self.fault.user}")
        if self.fault.password is not None:
            body["spec"]["containers"][0]["args"].append("--password")
            body["spec"]["containers"][0]["args"].append(f"{self.fault.password}")
        logger.debug(body)

        self.kubernetes_client.create_namespaced_pod(
            namespace="faults",
            body=body,
        )
        logger.info(f"execute mongodb fsync lock: {self.fault}")


    def recover(self):
        self.kubernetes_client.delete_namespaced_pod(
            namespace="faults",
            name=self.fault.uid,
        )
        logger.info(f"recover mongodb fsync lock")
