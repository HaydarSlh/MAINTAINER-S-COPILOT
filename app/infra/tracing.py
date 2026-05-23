"""Tracing backend adapter — wired from Day 1, not bolted on later.

Per the brief: every LLM call, tool call, and RAG retrieval is a span; a
conversation is a trace tree rooted at the user message. Span attributes
include model name, token counts, latency, and tool inputs/outputs AFTER
redaction. The trace ID is logged alongside every structured log line so logs
and traces are joinable.

Backend: OpenTelemetry → Jaeger (OTLP gRPC). Endpoint and service name come
from Vault (secret/tracing). The api refuses to boot if the endpoint is empty.
"""

from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.infra.vault import read_secret

_tracer: trace.Tracer | None = None


def init_tracing() -> None:
    """Configure the global OTEL tracer from Vault-resolved settings.

    Called once in app/main.py before the app starts serving.
    Raises RuntimeError if the endpoint is missing so the container exits.
    """
    global _tracer
    cfg = read_secret("secret/tracing")
    endpoint = cfg.get("endpoint", "").strip()
    service_name = cfg.get("service_name", "maintainers-copilot").strip()

    if not endpoint:
        raise RuntimeError(
            "Tracing endpoint is empty in Vault (secret/tracing.endpoint). "
            "Run scripts/vault_bootstrap.sh."
        )

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)


def _get_tracer() -> trace.Tracer:
    """Return the module-level tracer, raising if init_tracing() was not called."""
    if _tracer is None:
        raise RuntimeError("Tracing not initialised — call init_tracing() at boot.")
    return _tracer


@contextmanager
def span(name: str, attributes: dict | None = None):
    """Context manager that wraps a block in an OTEL span.

    Caller is responsible for passing only redacted attributes.
    """
    tracer = _get_tracer()
    with tracer.start_as_current_span(name) as s:
        if attributes:
            for k, v in attributes.items():
                s.set_attribute(k, v)
        yield s


def current_trace_id() -> str:
    """Return the hex trace ID of the current active span, or 'no-trace'."""
    ctx = trace.get_current_span().get_span_context()
    if ctx.is_valid:
        return format(ctx.trace_id, "032x")
    return "no-trace"
