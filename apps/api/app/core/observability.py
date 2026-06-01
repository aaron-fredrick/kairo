import structlog
from fastapi import FastAPI
from prometheus_client import make_asgi_app
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import logging
import sys

def setup_logging():
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def setup_metrics(app: FastAPI):
    # Add prometheus asgi middleware to route /metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

def setup_tracing(app: FastAPI):
    # Setup OpenTelemetry
    FastAPIInstrumentor.instrument_app(app)

def setup_observability(app: FastAPI):
    setup_logging()
    setup_metrics(app)
    setup_tracing(app)
