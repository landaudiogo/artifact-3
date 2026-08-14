import os
import time
import logging

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="[%(asctime)s] %(levelname)s\t- %(message)s"
)
logging.getLogger("httpx").setLevel("WARNING")
logging.getLogger("kubernetes").setLevel("WARNING")
logging.getLogger("httpcore").setLevel("WARNING")

from kubernetes import client, config
from httpx import Client, HTTPTransport

from .faults.service.cpu import CPUStress, CPUReduce
from .faults.service.memory import MemoryStress


def main() -> None:
    config.load_kube_config()

    # Set up prometheus client with 5 retries
    transport = HTTPTransport(retries=5)
    prometheus_client = Client(base_url="http://k8s-master:30954",transport=transport)

    memory_stress = MemoryStress(client.CustomObjectsApi(), {"namespace": "social-network", "label_selector": "app=post-storage-mongodb"})
    memory_stress.prepare()
    memory_stress.execute()
    time.sleep(15)
    memory_stress.recover()

    time.sleep(60)

    cpu_stress = CPUStress(client.CoreV1Api(), prometheus_client, {"namespace": "social-network", "label_selector": "app=post-storage-mongodb"})
    cpu_stress.prepare()
    cpu_stress.execute()
    time.sleep(60)
    cpu_stress.recover()

    time.sleep(60)

    cpu_reduce = CPUReduce(client.CoreV1Api(), prometheus_client, {"namespace": "social-network", "label_selector": "app=post-storage-mongodb"})
    cpu_reduce.prepare()
    cpu_reduce.execute()
    time.sleep(60)
    cpu_reduce.recover()

    # locust_requests_current_response_time_percentile_95

