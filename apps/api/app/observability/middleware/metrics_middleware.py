import time
from fastapi import Request
from opentelemetry import metrics

meter = metrics.get_meter("kairo.api")

# Metrics definitions (created once per process)
request_counter = meter.create_counter(
    "http_requests_total",
    description="Total number of HTTP requests"
)

request_duration = meter.create_histogram(
    "http_request_duration_ms",
    description="HTTP request latency in milliseconds"
)


async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration_ms = (time.time() - start_time) * 1000

    labels = {
        "method": request.method,
        "path": request.url.path,
        "status": str(response.status_code),
    }

    request_counter.add(1, attributes=labels)
    request_duration.record(duration_ms, attributes=labels)

    return response