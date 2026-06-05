import structlog
import logging
import sys
from opentelemetry.sdk._logs import LoggingHandler
from app.core.config import settings

def setup_logging():
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG)
    
    # Configure standard logging
    handlers = [logging.StreamHandler(sys.stdout)]
    if settings.OTEL_ENABLED:
        handlers.append(LoggingHandler())

    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        handlers=handlers
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
