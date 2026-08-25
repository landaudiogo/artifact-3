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

from .. import FaultTrait

logger = logging.getLogger(__name__)

FAULT_POD_TEMPLATE = Template('''
    apiVersion: v1
    kind: Pod
    metadata:
      name: {{ name }}
    spec:
      containers:
      - image: dclandau/postgres-fault:latest
        name: postgres-lock-contention
        args: 
        - "--host"
        - "{{ host }}"
        - "--port"
        - "{{ port }}"
        - "--user"
        - "{{ user }}"
        - "--password"
        - "{{ password }}"
        - "--database"
        - "{{ database }}"
        - "--table"
        - "{{ table }}"
        - "--lock-duration"
        - "{{ lock_duration }}"
        - "--interval"
        - "{{ interval }}"
''')


@dataclass
class PostgresLockContentionParameters:
    uid: str
    host: str 
    port: str 
    user: str 
    password: str 
    database: str 
    table: str 
    lock_duration: str 
    interval: str 


class PostgresLockContention(FaultTrait):


    def __init__(self, kubernetes_client, spec):
        self.kubernetes_client = kubernetes_client
        self.fault = PostgresLockContentionParameters(
            uid=str(uuid4()),
            host=spec["host"],
            port=spec["port"],
            user=spec["user"],
            password=spec["password"],
            database=spec["database"],
            table=spec["table"],
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
                user=self.fault.user, 
                password=self.fault.password, 
                database=self.fault.database, 
                table=self.fault.table, 
                lock_duration=self.fault.lock_duration, 
                interval=self.fault.interval, 
            ),
            Loader=SafeLoader,
        )
        logger.debug(body)
        self.kubernetes_client.create_namespaced_pod(
            namespace="faults",
            body=body,
        )
        logger.info(f"execute postgres lock contention: {self.fault}")


    def recover(self):
        self.kubernetes_client.delete_namespaced_pod(
            namespace="faults",
            name=self.fault.uid,
        )
        logger.info(f"recover postgres lock contention: {self.fault}")
