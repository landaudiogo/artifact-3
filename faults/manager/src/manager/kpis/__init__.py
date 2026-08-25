from jinja2 import Template


LATENCY_95_LOCUST_TEMPLATE = Template('''
    locust_requests_current_response_time_percentile_95{{ filter }}
''')

ERROR_LOCUST_TEMPLATE = Template('''
    sum (rate(locust_errors{{ filter }}[10s])) by (service)
''')

CONTAINER_START_WINDOW_LOCUST_TEMPLATE = Template('''
    (
      container_start_time_seconds{{ filter }}
      unless
      container_start_time_seconds{{ filter }} offset 5s
    ) > bool 0
''')
