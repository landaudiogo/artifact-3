from kubernetes import client, config
from httpx import Client, HTTPTransport

from . import FaultTrait

from .service.cpu import CPUStress, CPUReduce
from .service.memory import MemoryStress, MemoryReduce
from .service.net import NetworkPartition, NetworkBandwidth
from .service.deploy import DeletePods
from .service.block import BlockLatency

from .host.cpu import CPUStress as HostCPUStress
from .host.block import BlockLatency as HostBlockLatency
from .host.net import (
    NetworkPartition as HostNetworkPartition, 
    NetworkBandwidth as HostNetworkBandwidth
)
from .host.reboot import Reboot as HostReboot

from .application.postgres import PostgresLockContention
from .application.mongodb import MongodbFsyncLock


config.load_kube_config()




class Fault:
    @staticmethod
    def from_manifest(manifest) -> FaultTrait:
        transport = HTTPTransport(retries=5)
        prometheus_client = Client(base_url="http://k8s-master:30954",transport=transport)

        match manifest["type"]:
            case "service-cpu-stress":
                return CPUStress(client.CoreV1Api(), prometheus_client, manifest["spec"])
            case "service-cpu-reduce":
                return CPUReduce(client.CoreV1Api(), prometheus_client, manifest["spec"])
            case "service-memory-stress":
                return MemoryStress(client.CustomObjectsApi(), manifest["spec"])
            case "service-memory-reduce":
                return MemoryReduce(client.CoreV1Api(), prometheus_client, manifest["spec"])
            case "service-net-partition":
                return NetworkPartition(client.CustomObjectsApi(), manifest["spec"])
            case "service-net-bandwidth":
                return NetworkBandwidth(client.CoreV1Api(), client.CustomObjectsApi(), prometheus_client, manifest["spec"])
            case "service-delete-pods":
                return DeletePods(client.AppsV1Api(), manifest["spec"])
            case "service-block-latency":
                return BlockLatency(client.CoreV1Api(), manifest["spec"])
            case "host-cpu-stress":
                return HostCPUStress(manifest["spec"])
            case "host-block-latency":
                return HostBlockLatency(manifest["spec"])
            case "host-net-partition":
                return HostNetworkPartition(client.CustomObjectsApi(), prometheus_client, manifest["spec"],)
            case "host-net-bandwidth":
                return HostNetworkBandwidth(client.CustomObjectsApi(), prometheus_client, manifest["spec"])
                pass
            case "host-reboot":
                return HostReboot(manifest["spec"])
            case "postgres-table-lock":
                return PostgresLockContention(client.CoreV1Api(), manifest["spec"])
            case "mongodb-fsync-lock":
                return MongodbFsyncLock(client.CoreV1Api(), manifest["spec"])

    # application_mongodb = MongodbFsyncLock(
    #     client.CoreV1Api(), 
    #     {
    #         "host": "post-storage-mongodb.social-network",
    #         "port": "27017",
    #         "lock_duration": "0.4",
    #         "interval": "0.6",
    #     },
    # )
    # application_mongodb.prepare()
    # inject_start = time.time()
    # application_mongodb.execute()
    # time.sleep(60)
    # application_mongodb.recover()
    # inject_end = time.time()
    # print("social", social_network.impacted_period(inject_start, inject_end))
    # print("media", media_microservices.impacted_period(inject_start, inject_end))

    # application_postgres = PostgresLockContention(
    #     client.CoreV1Api(), 
    #     {
    #         "host": "postgresql.otel-demo",
    #         "port": "5432",
    #         "user": "root",
    #         "password": "otel",
    #         "database": "otel",
    #         "table": "catalog.products",
    #         "lock_duration": "0.2",
    #         "interval": "0.9",
    #     },
    # )
    # application_postgres.prepare()
    # application_postgres.execute()
    # time.sleep(60)
    # application_postgres.recover()

    # host_reboot = HostReboot({"node": "k8s-worker2"})
    # host_reboot.prepare()
    # host_reboot.execute()
    # host_reboot.recover()

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
    # inject_start = time.time()
    # host_cpu_stress.execute()
    # time.sleep(60)
    # host_cpu_stress.recover()
    # inject_end = time.time()

    # block_latency = BlockLatency(client.CoreV1Api(), {"namespace": "otel-demo", "label_selector": "opentelemetry.io/name=postgresql"})
    # block_latency.prepare()
    # block_latency.execute()
    # time.sleep(60)
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
    # inject_start = time.time()
    # cpu_stress.execute()
    # time.sleep(60)
    # cpu_stress.recover()
    # inject_end = time.time()
    # for application, kpis in applications.items():
    #     print(application, kpis.impacted_period(inject_start, inject_end))

    # time.sleep(60)

    # cpu_reduce = CPUReduce(client.CoreV1Api(), prometheus_client, {"namespace": "social-network", "label_selector": "app=post-storage-mongodb"})
    # cpu_reduce.prepare()
    # cpu_reduce.execute()
    # time.sleep(60)
    # cpu_reduce.recover()

    # locust_requests_current_response_time_percentile_95
    # sum (rate(locust_errors[10s])) by (namespace)
