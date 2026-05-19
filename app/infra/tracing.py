"""Tracing backend adapter — wired from Day 1, not bolted on later.

Per the brief: every LLM call, tool call, and RAG retrieval is a span; a
conversation is a trace tree rooted at the user message. Span attributes
include model name, token counts, latency, and tool inputs/outputs AFTER
redaction. The trace ID is logged alongside every structured log line so logs
and traces are joinable. Backend choice + defense in DECISIONS.md D9.

api refuses to boot if the tracing backend is misconfigured.
"""

# TODO: init backend client from Vault-resolved key
# TODO: span() context manager; current_trace_id() for log correlation
# TODO: ensure inputs/outputs pass through app/infra/redaction before recording


def current_trace_id() -> str:
    raise NotImplementedError
