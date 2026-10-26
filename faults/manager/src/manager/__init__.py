import os
import time
import logging

from manager.faults import HostRestart, NamespaceRestart

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

from .applications import Application


class Controller:

    def __init__(self, faults=None):
        prometheus_client = AsyncClient(base_url=os.getenv("PROMETHEUS_URL"), transport=AsyncHTTPTransport(retries=5))
        self.applications = [
            Application(Path(os.getenv("BENCHMARK_MANIFESTS_DIR")), "social-network", os.getenv("LOCUST_SOCIAL_NETWORK"), prometheus_client),
            Application(Path(os.getenv("BENCHMARK_MANIFESTS_DIR")), "media-microservices", os.getenv("LOCUST_MEDIA_MICROSERVICES"), prometheus_client),
            Application(Path(os.getenv("BENCHMARK_MANIFESTS_DIR")), "hotel-reservation", os.getenv("LOCUST_HOTEL_RESERVATION"), prometheus_client),
            Application(Path(os.getenv("BENCHMARK_MANIFESTS_DIR")), "online-boutique", os.getenv("LOCUST_ONLINE_BOUTIQUE"), prometheus_client),
            Application(Path(os.getenv("BENCHMARK_MANIFESTS_DIR")), "otel-demo", os.getenv("LOCUST_OTEL_DEMO"), prometheus_client),
        ]

        if faults is None:
            faults = []
        self.faults = faults
        self.fault_creator = Fault()


    async def bootstrap(self):
        ready_handles, load_handles = [], []
        for application in self.applications:
            application.deploy()
            ready_handles.append(application.wait_for_ready())
            load_handles.append(application.set_load(10, attempts=5))
        await asyncio.gather(*ready_handles)
        await asyncio.gather(*load_handles)

    async def create_baseline(
        self,
        baseline_interval: timedelta = timedelta(minutes=1),
        deadline: timedelta = timedelta(minutes=5),
        backoff_interval: timedelta = timedelta(seconds=10),
        attempts: int = 2,
    ):
        for attempt in range(attempts):
            end = datetime.now() + deadline
            while datetime.now() < end:
                violating_applications = set()
                end_epoch = time.time()
                start_epoch = end_epoch - baseline_interval.total_seconds()
                logger.debug(f"attempting new baseline period [{start_epoch}; {end_epoch}]")
                stability_handles, slo_latency_handles, set_baseline_handles = [], [], []
                for application in self.applications:
                    stability_handles.append(application.stable(start_epoch, end_epoch))
                    slo_latency_handles.append(application.slo_latency(start_epoch, end_epoch))
                    set_baseline_handles.append(application.set_baseline_latency(start_epoch, end_epoch))

                unstable = [application
                    for application, stable in zip(self.applications, await asyncio.gather(*stability_handles))
                    if not stable
                ]
                if len(unstable) > 0:
                    unstable_applications = [application.microservice_benchmark for application in unstable]
                    violating_applications.update(unstable_applications)
                    logger.debug(f"{unstable_applications} are unstable")

                    # Suppress 'not awaited for' runtime error
                    for latency_coroutine, set_baseline_coroutine in zip(slo_latency_handles, set_baseline_handles):
                        latency_coroutine.close()
                        set_baseline_coroutine.close()

                    await asyncio.sleep(backoff_interval.total_seconds())
                    continue

                latency_violations = [application
                    for application, slo_latency in zip(self.applications, await asyncio.gather(*slo_latency_handles))
                    if not slo_latency
                ]
                if len(latency_violations) > 0:
                    slow_applications = [application.microservice_benchmark for application in latency_violations]
                    violating_applications.update(slow_applications)
                    logger.debug(f"{slow_applications} do not satisfy latency SLO")

                    # Suppress 'not awaited for' runtime error
                    for set_baseline_coroutine in set_baseline_handles:
                        set_baseline_coroutine.close()

                    await asyncio.sleep(backoff_interval.total_seconds())
                    continue

                set_baseline_results = await asyncio.gather(*set_baseline_handles)
                if not all(set_baseline_results):
                    await asyncio.sleep(backoff_interval.total_seconds())
                    continue

                logger.info(f"found new baseline period [{start_epoch}; {end_epoch}]")
                return True

            # We don't want to restart when we no longer have any more attempts
            if attempt == attempts-1:
                break

            logger.info(f"failed to find baseline within deadline: restarting {violating_applications}")
            await self.restart_applications(violating_applications)

        return False

    async def restart_applications(self, application_names):
        wait_ready_handles, set_load_handles = [], []
        for application in self.applications:
            if application.microservice_benchmark not in application_names:
                continue
            load = application.load
            application.destroy()
            application.deploy()
            wait_ready_handles.append(application.wait_for_ready())
            set_load_handles.append(application.set_load(load, attempts=5))
        await asyncio.gather(*wait_ready_handles)
        await asyncio.gather(*set_load_handles)

    async def inject_fault(self, fault, fault_interval: timedelta = timedelta(minutes=1)):
        fault = self.fault_creator.from_manifest(fault)
        fault.prepare()
        start_epoch = time.time()
        fault.execute()
        await asyncio.sleep(fault_interval.total_seconds())
        fault.recover()
        end_epoch = time.time()
        logger.info(f"fault injection interval [{start_epoch}; {end_epoch}]")
        error_handles, restart_handles, latency_handles = [], [], []
        for application in self.applications:
            error_handles.append(application.slo_error(start_epoch, end_epoch))
            restart_handles.append(application.restarted_pods(start_epoch, end_epoch))
            latency_handles.append(application.slo_latency(start_epoch, end_epoch))

        for restarts, application in zip(await asyncio.gather(*restart_handles), self.applications):
            if (len(restarts) > 0) and (fault.expected_restarts() not in [HostRestart(), NamespaceRestart(application.microservice_benchmark)]):
                logger.warning(f"{application.microservice_benchmark} had unexpected restarts")
            elif (len(restarts) == 0) and (fault.expected_restarts() in [HostRestart(), NamespaceRestart(application.microservice_benchmark)]):
                logger.warning(f"{application.microservice_benchmark} had no expected restarts")
            elif (len(restarts) > 0) and (fault.expected_restarts() in [HostRestart(), NamespaceRestart(application.microservice_benchmark)]):
                logger.info(f"{application.microservice_benchmark} has restarts for {fault.expected_restarts()}")

        error_violations = [
            application.microservice_benchmark
            for error_slo, application in zip(await asyncio.gather(*error_handles), self.applications)
            if not error_slo
        ]
        if len(error_violations) > 0:
            logger.info(f"{error_violations} had error SLO violations during fault injection period")

        latency_violations = [
            application.microservice_benchmark
            for latency_slo, application in zip(await asyncio.gather(*latency_handles), self.applications)
            if not latency_slo
        ]
        if len(latency_violations) > 0:
            logger.info(f"{latency_violations} had latency SLO violations during fault injection period")

    def control_loop(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.bootstrap())

        for fault in self.faults:
            loop.run_until_complete(self.create_baseline())
            loop.run_until_complete(self.inject_fault(fault))

        # self.cleanup()

    def cleanup(self):
        for application in self.applications:
            application.destroy()

def main() -> None:
    faults = [
        {
            "type": "host-reboot",
            "spec": {
                "node": "k8s-worker3",
            }
        },
        {
            "type": "service-memory-reduce",
            "spec": {
                "namespace": "online-boutique",
                "label_selector": "app=frontend"
            }
        },
        {
            "type": "service-block-latency",
            "spec": {
                "namespace": "media-microservices",
                "label_selector": "app=review-storage-mongodb"
            }
        },
        {
            "type": "service-cpu-stress",
            "spec": {
                "namespace": "social-network",
                "label_selector": "app=post-storage-mongodb"
            }
        },
    ]

    controller = Controller(faults=faults)
    controller.control_loop()
    return


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
