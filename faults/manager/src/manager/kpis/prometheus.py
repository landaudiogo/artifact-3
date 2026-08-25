import numpy as np
import logging
import httpx
import json

from . import LATENCY_95_LOCUST_TEMPLATE, ERROR_LOCUST_TEMPLATE
from .stats import has_effect

logger = logging.getLogger(__name__)

class PrometheusKPIs:
    def __init__(
        self,
        start,
        end,
        prometheus_client,
        latency_filter,
        error_filter,
    ):
        self.prometheus_client = prometheus_client
        self.latency_filter = latency_filter
        self.error_filter = error_filter

        self.baseline_latency = None
        self.baseline_error = None
        self.set_baseline(start, end)

    def set_baseline(self, start, end):
        self.baseline_latency = self.latency_query(start, end)
        self.baseline_error = self.error_query(start, end)

    def prometheus_query(self, start, end, query):
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

        res = json.loads(res.text)["data"]["result"]
        assert len(res) == 1, f"Query returned more than 1 metric. Try adjusting the filter parameters: {query}"
        res = res[0]
        return [float(value[1]) for value in res["values"]]


    def error_query(self, start, end):
        query = ERROR_LOCUST_TEMPLATE.render(filter=self.error_filter)
        return self.prometheus_query(start, end, query)

    def latency_query(self, start, end):
        query = LATENCY_95_LOCUST_TEMPLATE.render(filter=self.latency_filter)
        return self.prometheus_query(start, end, query)

    def impacted_period(self, start, end):
        compare_latency = self.latency_query(start, end)
        latency_increased = has_effect(self.baseline_latency, compare_latency)

        compare_error = self.error_query(start, end)
        errors_increased = has_effect(self.baseline_error, compare_error)
        
        return latency_increased or errors_increased
