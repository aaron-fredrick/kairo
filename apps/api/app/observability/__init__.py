from typing import Optional
from fastapi import FastAPI

from app.observability.metrics import setup_metrics
from app.observability.tracing import setup_tracing
from app.observability.logging import setup_logging

from .otel import setup_otel

from . import middleware

def setup(app: Optional[FastAPI] = None) -> None:
	"""
	Convenience wrapper to configure observability.
	Always configures logging; if `app` is provided, also configures tracing and metrics.
	"""
	setup_logging()
	if app is not None:
		setup_metrics(app)
  
		setup_otel(app)
  
		setup_tracing(app)

__all__ = ["setup", "middleware"]