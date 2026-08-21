import os
import time
import logging

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="[%(asctime)s] %(levelname)s - %(message)s"
)
logging.getLogger("httpx").setLevel("WARNING")
logging.getLogger("kubernetes").setLevel("WARNING")
logging.getLogger("httpcore").setLevel("WARNING")

from kubernetes import client, config
from httpx import Client, HTTPTransport

from .faults.service.cpu import CPUStress, CPUReduce
from .faults.service.memory import MemoryStress, MemoryReduce
from .faults.service.net import NetworkPartition, NetworkBandwidth
from .faults.service.deploy import DeletePods
from .faults.service.block import BlockLatency

from .faults.host.cpu import CPUStress as HostCPUStress
from .faults.host.block import BlockLatency as HostBlockLatency
from .faults.host.net import (
    NetworkPartition as HostNetworkPartition, 
    NetworkBandwidth as HostNetworkBandwidth
)
from .faults.host.reboot import Reboot as HostReboot


def main() -> None:
    config.load_kube_config()

    # Set up prometheus client with 5 retries
    transport = HTTPTransport(retries=5)
    prometheus_client = Client(base_url="http://k8s-master:30954",transport=transport)

    host_reboot = HostReboot({"node": "k8s-worker2"})
    host_reboot.prepare()
    host_reboot.execute()
    host_reboot.recover()

    # host_network_bandwidth = HostNetworkBandwidth(client.CustomObjectsApi(), prometheus_client, {
    #     "node": "k8s-worker3",
    #     "device": "enp0s31f6",
    #     "limit": "50 MiB",
    #     "buffer": "1 MiB",
    # })
    # host_network_bandwidth.prepare()
    # host_network_bandwidth.execute()
    # time.sleep(60)
    # host_network_bandwidth.recover()

    # host_network_partition = HostNetworkPartition(
    #     client.CustomObjectsApi(), 
    #     prometheus_client, 
    #     {
    #         "node": "k8s-worker1",
    #         "destination_node": "k8s-worker3",
    #     },
    # )
    # host_network_partition.prepare()
    # host_network_partition.execute()
    # time.sleep(60)
    # host_network_partition.recover()

    # host_block_latency = HostBlockLatency({"node": "k8s-worker1"})
    # host_block_latency.prepare()
    # host_block_latency.execute()
    # time.sleep(60)
    # host_block_latency.recover()

    # host_cpu_stress = HostCPUStress({"node": "k8s-worker1"})
    # host_cpu_stress.prepare()
    # host_cpu_stress.execute()
    # time.sleep(60)
    # host_cpu_stress.recover()

    # block_latency = BlockLatency(client.CoreV1Api(), {"namespace": "social-network", "label_selector": "app=post-storage-mongodb"})
    # block_latency.prepare()
    # block_latency.execute()
    # time.sleep(15)
    # block_latency.recover()

    # delete_pods = DeletePods(client.AppsV1Api(), {"namespace": "social-network", "label_selector": "service=post-storage-mongodb"})
    # delete_pods.prepare()
    # delete_pods.execute()
    # time.sleep(60)
    # delete_pods.recover()

    # network_bandwidth = NetworkBandwidth(client.CoreV1Api(), client.CustomObjectsApi(), prometheus_client, {"namespace": "social-network", "label_selector": "app=post-storage-mongodb"})
    # network_bandwidth.prepare()
    # network_bandwidth.execute()
    # time.sleep(60)
    # network_bandwidth.recover()

    # network_partition = NetworkPartition(client.CustomObjectsApi(), {"namespace": "social-network", "label_selector": "app=post-storage-mongodb"})
    # network_partition.prepare()
    # network_partition.execute()
    # time.sleep(60)
    # network_partition.recover()

    # memory_reduce = MemoryReduce(client.CoreV1Api(), prometheus_client, {"namespace": "social-network", "label_selector": "app=post-storage-mongodb"})
    # memory_reduce.prepare()
    # memory_reduce.execute()
    # time.sleep(15)
    # memory_reduce.recover()

    # time.sleep(60)

    # memory_stress = MemoryStress(client.CustomObjectsApi(), {"namespace": "social-network", "label_selector": "app=post-storage-mongodb"})
    # memory_stress.prepare()
    # memory_stress.execute()
    # time.sleep(15)
    # memory_stress.recover()

    # time.sleep(60)

    # cpu_stress = CPUStress(client.CoreV1Api(), prometheus_client, {"namespace": "social-network", "label_selector": "app=post-storage-mongodb"})
    # cpu_stress.prepare()
    # cpu_stress.execute()
    # time.sleep(60)
    # cpu_stress.recover()

    # time.sleep(60)

    # cpu_reduce = CPUReduce(client.CoreV1Api(), prometheus_client, {"namespace": "social-network", "label_selector": "app=post-storage-mongodb"})
    # cpu_reduce.prepare()
    # cpu_reduce.execute()
    # time.sleep(60)
    # cpu_reduce.recover()

    # locust_requests_current_response_time_percentile_95
    # sum (rate(locust_errors[10s])) by (namespace)
