from typing import Optional
from fastapi import FastAPI

from app.observability.metrics import setup_metrics
from app.observability.tracing import setup_tracing
from app.observability.logging import setup_logging

def setup(app: Optional[FastAPI] = None) -> None:
	"""
	Convenience wrapper to configure observability.
	Always configures logging; if `app` is provided, also configures tracing and metrics.
	"""
	setup_logging()
	if app is not None:
		setup_tracing(app)
		setup_metrics(app)

__all__ = ["setup"]