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

import asyncio

from datetime import datetime, timedelta
from httpx import AsyncClient, AsyncHTTPTransport
from pathlib import Path

from .faults.fault import Fault

from .kpis.prometheus import PrometheusKPIs
from .applications.online_boutique import OnlineBoutique

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
    transport = AsyncHTTPTransport(retries=5)
    prometheus_client = AsyncClient(base_url=os.getenv("PROMETHEUS_URL"),transport=transport)

    online_boutique = OnlineBoutique(
        Path(os.getenv("MANIFEST_ONLINE_BOUTIQUE")),
        os.getenv("LOCUST_ONLINE_BOUTIQUE"),
        prometheus_client,
    )
    if not online_boutique.deploy():
        return

    loop = asyncio.get_event_loop()
    wait_for_ready = asyncio.gather(
        online_boutique.wait_for_ready(),
    )
    loop.run_until_complete(wait_for_ready)
    loop.run_until_complete(online_boutique.set_load(20))
    time.sleep(120)
    if not online_boutique.destroy():
        return
    return

    transport = HTTPTransport(retries=5)
    prometheus_client = Client(base_url="http://k8s-master:30954",transport=transport)
    baseline_start, baseline_end = 1787646931.5262878, 1787647122.984789

    applications = {
        "social_network": PrometheusKPIs(
            baseline_start,
            baseline_end,
            prometheus_client,
            '{ service="locust-social-network" }',
            '{ service="locust-social-network" }',
            '{ namespace="social-network" }',
        ),
        "media_microservices": PrometheusKPIs(
            baseline_start,
            baseline_end,
            prometheus_client,
            '{ service="locust-media-microservices" }',
            '{ service="locust-media-microservices" }',
            '{ namespace="media-microservices" }',
        ),
        "online_boutique": PrometheusKPIs(
            baseline_start,
            baseline_end,
            prometheus_client,
            '{ service="locust-online-boutique" }',
            '{ service="locust-online-boutique" }',
            '{ namespace="online-boutique" }',
        ),
        "otel_demo": PrometheusKPIs(
            baseline_start,
            baseline_end,
            prometheus_client,
            '{ service="locust-otel-demo" }',
            '{ service="locust-otel-demo" }',
            '{ namespace="otel-demo" }',
        ),
        "hotel_reservation": PrometheusKPIs(
            baseline_start,
            baseline_end,
            prometheus_client,
            '{ service="locust-hotel-reservation" }',
            '{ service="locust-hotel-reservation" }',
            '{ namespace="hotel-reservation" }',
        ),
    }

    faults = [
        {
            "type": "service-cpu-stress",
            "spec": {
                "namespace": "social-network",
                "label_selector": "app=post-storage-mongodb"
            }
        },
        {
            "type": "service-block-latency",
            "spec": {
                "namespace": "media-microservices",
                "label_selector": "app=review-storage-mongodb"
            }
        }
    ]

    recover(applications, timedelta(minutes=5))
    # for fault_manifest in faults:
    #     recover(applications, timedelta(minutes=5))
    #     fault = Fault.from_manifest(fault_manifest)
    #     fault.prepare()

    #     inject_start = time.time()
    #     print("=== BASELINE ===")
    #     for application, kpis in applications.items():
    #         impacted = kpis.impacted_period(inject_start-60, inject_start)
    #         print(application, impacted)

    #     fault.execute()
    #     time.sleep(60)
    #     fault.recover()
    #     inject_end = time.time()

    #     print("=== COMPARE ===")
    #     for application, kpis in applications.items():
    #         impacted = kpis.impacted_period(inject_start, inject_end)
    #         print(application, impacted)
