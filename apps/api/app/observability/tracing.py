from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def setup_tracing(app: FastAPI):
    # Setup OpenTelemetry
    FastAPIInstrumentor.instrument_app(app)