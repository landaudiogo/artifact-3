import os
import time
import logging

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logging.getLogger("httpx").setLevel("WARNING")
logging.getLogger("kubernetes").setLevel("WARNING")
logging.getLogger("httpcore").setLevel("WARNING")
logging.getLogger("asyncio").setLevel("WARNING")
logger = logging.getLogger(__name__)

import asyncio

from datetime import datetime, timedelta
from httpx import AsyncClient, AsyncHTTPTransport
from pathlib import Path

from .faults.fault import Fault

from .kpis.prometheus import PrometheusKPIs
from .applications import Application


class Controller:

    def __init__(self):
        prometheus_client = AsyncClient(base_url=os.getenv("PROMETHEUS_URL"), transport=AsyncHTTPTransport(retries=5))
        self.applications = [
            Application(Path(os.getenv("BENCHMARK_MANIFESTS_DIR")), "social-network", os.getenv("LOCUST_SOCIAL_NETWORK"), prometheus_client),
            Application(Path(os.getenv("BENCHMARK_MANIFESTS_DIR")), "media-microservices", os.getenv("LOCUST_MEDIA_MICROSERVICES"), prometheus_client),
            Application(Path(os.getenv("BENCHMARK_MANIFESTS_DIR")), "hotel-reservation", os.getenv("LOCUST_HOTEL_RESERVATION"), prometheus_client),
            Application(Path(os.getenv("BENCHMARK_MANIFESTS_DIR")), "online-boutique", os.getenv("LOCUST_ONLINE_BOUTIQUE"), prometheus_client),
            Application(Path(os.getenv("BENCHMARK_MANIFESTS_DIR")), "otel-demo", os.getenv("LOCUST_OTEL_DEMO"), prometheus_client),
        ]

    async def bootstrap(self):
        ready_handles, load_handles = [], []
        for application in self.applications:
            application.deploy()
            ready_handles.append(application.wait_for_ready())
            load_handles.append(application.set_load(10, attempts=5))
        await asyncio.gather(*ready_handles)
        await asyncio.gather(*load_handles)

    def control_loop(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.bootstrap())

        time.sleep(120)
        while True:
            pass

        self.cleanup()

    def cleanup(self):
        for application in self.applications:
            application.destroy()

def recover(applications, deadline=timedelta(minutes=5)):
    end = datetime.now() + deadline
    while datetime.now() < end:
        application_recovery = {}
        current_epoch = time.time()
        recovered = True
        for application, kpis in applications.items():
            impacted = kpis.impacted_period(current_epoch-60, current_epoch)
            # The window to evaluate restarts is slightly bigger
            containers_started = kpis.containers_started(current_epoch-80, current_epoch)
            application_recovery[application] = {"kpis": impacted, "containers_started": containers_started}
            if impacted or containers_started:
                recovered = False
            if not containers_started:
                kpis.set_baseline_latency(current_epoch-60, current_epoch)

        print("recovery status:", application_recovery)
        if recovered:
            return
        time.sleep(10)
    raise Exception("could not recover within deadline")


def main() -> None:
    controller = Controller()
    controller.control_loop()
    return

    # transport = HTTPTransport(retries=5)
    # prometheus_client = Client(base_url="http://k8s-master:30954",transport=transport)
    # baseline_start, baseline_end = 1787646931.5262878, 1787647122.984789

    # applications = {
    #     "social_network": PrometheusKPIs(
    #         baseline_start,
    #         baseline_end,
    #         prometheus_client,
    #         '{ service="locust-social-network" }',
    #         '{ service="locust-social-network" }',
    #         '{ namespace="social-network" }',
    #     ),
    #     "media_microservices": PrometheusKPIs(
    #         baseline_start,
    #         baseline_end,
    #         prometheus_client,
    #         '{ service="locust-media-microservices" }',
    #         '{ service="locust-media-microservices" }',
    #         '{ namespace="media-microservices" }',
    #     ),
    #     "online_boutique": PrometheusKPIs(
    #         baseline_start,
    #         baseline_end,
    #         prometheus_client,
    #         '{ service="locust-online-boutique" }',
    #         '{ service="locust-online-boutique" }',
    #         '{ namespace="online-boutique" }',
    #     ),
    #     "otel_demo": PrometheusKPIs(
    #         baseline_start,
    #         baseline_end,
    #         prometheus_client,
    #         '{ service="locust-otel-demo" }',
    #         '{ service="locust-otel-demo" }',
    #         '{ namespace="otel-demo" }',
    #     ),
    #     "hotel_reservation": PrometheusKPIs(
    #         baseline_start,
    #         baseline_end,
    #         prometheus_client,
    #         '{ service="locust-hotel-reservation" }',
    #         '{ service="locust-hotel-reservation" }',
    #         '{ namespace="hotel-reservation" }',
    #     ),
    # }

    # faults = [
    #     {
    #         "type": "service-cpu-stress",
    #         "spec": {
    #             "namespace": "social-network",
    #             "label_selector": "app=post-storage-mongodb"
    #         }
    #     },
    #     {
    #         "type": "service-block-latency",
    #         "spec": {
    #             "namespace": "media-microservices",
    #             "label_selector": "app=review-storage-mongodb"
    #         }
    #     }
    # ]

    # recover(applications, timedelta(minutes=5))
    # # for fault_manifest in faults:
    # #     recover(applications, timedelta(minutes=5))
    # #     fault = Fault.from_manifest(fault_manifest)
    # #     fault.prepare()

    # #     inject_start = time.time()
    # #     print("=== BASELINE ===")
    # #     for application, kpis in applications.items():
    # #         impacted = kpis.impacted_period(inject_start-60, inject_start)
    # #         print(application, impacted)

    # #     fault.execute()
    # #     time.sleep(60)
    # #     fault.recover()
    # #     inject_end = time.time()

    # #     print("=== COMPARE ===")
    # #     for application, kpis in applications.items():
    # #         impacted = kpis.impacted_period(inject_start, inject_end)
    # #         print(application, impacted)
