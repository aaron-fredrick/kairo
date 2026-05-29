import logging
import sys
from app_backend.core.config import settings

_LOG_LEVEL = logging.DEBUG if settings.DEBUG else logging.INFO

_formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_formatter)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger pre-configured with the application log level."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_handler)
    logger.setLevel(_LOG_LEVEL)
    logger.propagate = False
    return logger
