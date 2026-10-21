import numpy as np
import logging
import httpx
import json
import random
import time

from jinja2 import Template
from typing import Optional
from httpx import AsyncClient

from .stats import has_effect

logger = logging.getLogger(__name__)


LOCUST_LATENCY_95_TEMPLATE = Template('''
    locust_requests_current_response_time_percentile_95{ service="{{ service }}" }
''')

LOCUST_USERS_TEMPLATE = Template('''
    locust_users{ service="{{ service }}" }
''')

LOCUST_ERROR_RATE_TEMPLATE = Template('''
    rate(locust_requests_num_failures{ name='Aggregated', service="{{ service }}" }[10s]) 
    / rate(locust_requests_num_requests{ name='Aggregated', service="{{ service }}" }[10s])
''')

CONTAINER_START_WINDOW_TEMPLATE = Template('''
    max by (pod) (
      (
        (
          container_start_time_seconds{ namespace = "{{ namespace }}", container != "" }
          unless
          container_start_time_seconds{ namespace = "{{ namespace }}", container != "" } offset 10s
        ) > bool 0
      )
      or
      (
        container_start_time_seconds{ namespace = "{{ namespace }}", container != "" } * 0
      )
    )
''')

class PrometheusKPIs:
    def __init__(
        self,
        start,
        end,
        prometheus_client,
        latency_filter,
        error_filter,
        container_start_window_filter,
        nsamples=60,
    ):
        self.prometheus_client = prometheus_client
        self.latency_filter = latency_filter
        self.error_filter = error_filter
        self.container_start_window_filter = container_start_window_filter
        self.nsamples = nsamples

        self.baseline_latency = []
        self.baseline_error = []
        self._set_baseline(start, end)

    def _set_baseline(self, start, end):
        self._set_baseline_error(start, end)
        self.set_baseline_latency(start, end)

    def _set_baseline_error(self, start, end):
        self.baseline_error.extend(self.latency_query(start, end))
        self.baseline_error = self.baseline_error if self.nsamples >= len(self.baseline_error) else random.sample(self.baseline_error, self.nsamples)

    def set_baseline_latency(self, start, end):
        self.baseline_latency.extend(self.latency_query(start, end))
        self.baseline_latency = self.baseline_latency if self.nsamples >= len(self.baseline_latency) else random.sample(self.baseline_latency, self.nsamples)

    def _prometheus_query(self, start, end, query):
        res = self.prometheus_client.get(
            "/api/v1/query_range",
            params={
                "query": query,
                "start": start,
                "end": end,
                "step": 1
            },
        )
        if res.status_code != httpx.codes.OK:
            logger.error(f"prometheus query failed: {res.status_code} {res.text}")
            raise Exception("Prometheus")

        return json.loads(res.text)["data"]["result"]

    def _extract_float_values(self, prometheus_result):
        return 

    def error_query(self, start, end):
        query = ERROR_LOCUST_TEMPLATE.render(filter=self.error_filter)
        result = self._prometheus_query(start, end, query)
        assert len(result) == 1, f"Query returned more than 1 metric. Try adjusting the error_filter parameter: {query}"
        return [float(value[1]) for value in result[0]["values"]]

    def latency_query(self, start, end):
        query = LATENCY_95_LOCUST_TEMPLATE.render(filter=self.latency_filter)
        result = self._prometheus_query(start, end, query)
        assert len(result) == 1, f"Query returned more than 1 metric. Try adjusting the latency_filter parameter: {query}"
        return [float(value[1]) for value in result[0]["values"]]

    def containers_started(self, start, end):
        query = CONTAINER_START_WINDOW_LOCUST_TEMPLATE.render(filter=self.container_start_window_filter)
        result = self._prometheus_query(start, end, query)
        return len(result) > 0

    def impacted_period(self, start, end):
        compare_latency = self.latency_query(start, end)
        latency_increased = has_effect(self.baseline_latency, compare_latency)
        median_baseline_latency = np.median(np.array(self.baseline_latency))
        median_compare_latency = np.median(np.array(compare_latency))

        compare_error = self.error_query(start, end)
        errors_increased = has_effect(self.baseline_error, compare_error)
        median_baseline_error = np.median(np.array(self.baseline_error))
        median_compare_error = np.median(np.array(compare_error))

        print(f"latency: {median_baseline_latency} {median_compare_latency} -> {latency_increased}\terrors: {median_baseline_error} {median_compare_error} -> {errors_increased}")
        
        return latency_increased or errors_increased

class PrometheusMetric:


    def __init__(self, prometheus_client: AsyncClient, query: str):
        self.prometheus_client = prometheus_client
        self.promql_query = query


    async def query(self, time_epoch: Optional[int] = None):
        '''Prometheus query.
        
        parameters:
            time: epoch timestamp reference
        '''
        if time_epoch is None:
            time_epoch = time.time()

        res = await self.prometheus_client.get(
            "/api/v1/query",
            params={
                "query": self.promql_query,
                "time": time_epoch,
            },
        )
        if res.status_code != httpx.codes.OK:
            logger.error(f"prometheus query failed: {res.status_code} {res.text}")
            raise Exception("Prometheus")

        return res.json()["data"]["result"]

    async def query_range(self, start_epoch: int, end_epoch: int):
        '''Prometheus query range.
        
        parameters:
            start: start unix epoch.
            end: end unix epoch.
        '''
        res = await self.prometheus_client.get(
            "/api/v1/query_range",
            params={
                "query": self.promql_query,
                "start": start_epoch,
                "end": end_epoch,
                "step": 1 # second granularity
            },
        )
        if res.status_code != httpx.codes.OK:
            logger.error(f"prometheus query failed: {res.status_code} {res.text}")
            raise Exception("Prometheus")

        return res.json()["data"]["result"]
