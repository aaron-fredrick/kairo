from fastapi import FastAPI
from prometheus_client import make_asgi_app

def setup_metrics(app: FastAPI):
    # Add prometheus asgi middleware to route /metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
