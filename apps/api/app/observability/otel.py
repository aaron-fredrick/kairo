from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader


def setup_otel(app):

    resource = Resource.create({
        "service.name": "kairo-api"
    })

    # ---------------- TRACES ----------------
    trace_provider = TracerProvider(resource=resource)

    trace_exporter = OTLPSpanExporter(
        endpoint="http://otel-collector:4318/v1/traces"
    )

    trace_provider.add_span_processor(
        BatchSpanProcessor(trace_exporter)
    )

    trace.set_tracer_provider(trace_provider)

    # ---------------- METRICS ----------------
    metric_exporter = OTLPMetricExporter(
        # TODO: make endpoint configurable and support gRPC exporter as well
        endpoint="http://otel-collector:4318/v1/metrics"
    )

    metric_reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis=5000
    )

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader]
    )

    metrics.set_meter_provider(meter_provider)