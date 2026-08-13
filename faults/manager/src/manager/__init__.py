import os
import time
import logging

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.getLogger("httpx").setLevel("WARNING")
logging.getLogger("kubernetes").setLevel("WARNING")
logging.getLogger("httpcore").setLevel("WARNING")

from kubernetes import client, config
from httpx import Client, HTTPTransport

from .faults.service.cpu import CPUStress, CPUReduce


def main() -> None:
    config.load_kube_config()

    kubernetes_client = client.CoreV1Api()

    # Set up prometheus client with 5 retries
    transport = HTTPTransport(retries=5)
    prometheus_client = Client(base_url="http://k8s-master:30954",transport=transport)

    # cpu_stress = CPUStress(kubernetes_client, prometheus_client, {"namespace": "social-network", "label_selector": "app=post-storage-service"})
    # cpu_stress.prepare()
    # cpu_stress.execute()
    # time.sleep(60)
    # cpu_stress.recover()

    cpu_reduce = CPUReduce(kubernetes_client, prometheus_client, {"namespace": "social-network", "label_selector": "app=post-storage-service"})
    cpu_reduce.prepare()
    cpu_reduce.execute()
    time.sleep(60)
    cpu_reduce.recover()
