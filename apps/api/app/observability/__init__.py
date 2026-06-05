from typing import Optional
from fastapi import FastAPI

from app.core.config import settings
from app.observability.metrics import setup_metrics
from app.observability.tracing import setup_tracing
from app.observability.logging import setup_logging

from .otel import setup_otel

from . import middleware

def setup(app: Optional[FastAPI] = None) -> None:
	"""
	Convenience wrapper to configure observability.
	Always configures logging; if `app` is provided, also configures tracing and metrics.
	OTLP Exporters are only attached if OTEL_ENABLED is True.
	"""
	setup_logging()
	if app is not None:
		setup_metrics(app)
		setup_tracing(app)
  
		if settings.OTEL_ENABLED:
			setup_otel(app)

__all__ = ["setup", "middleware"]