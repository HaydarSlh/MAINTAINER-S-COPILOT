"""HTTP client to the `modelserver` service (classifier / NER / summarizer).

Pipelines live behind FastAPI endpoints — called over HTTP, never imported
in-process from the api. If modelserver is down, raises ModelServerError and
the chat service degrades gracefully. Every call is a trace span.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.infra.tracing import span as trace_span


class ModelServerError(Exception):
    pass


def _base() -> str:
    return settings.modelserver_url.rstrip("/")


async def _post(path: str, payload: dict) -> dict:
    url = f"{_base()}{path}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise ModelServerError(f"modelserver {path} returned {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise ModelServerError(f"modelserver unreachable ({e})") from e


async def classify(text: str) -> dict:
    """POST /classify → {label, label_id, confidence, all_scores}."""
    with trace_span("modelserver.classify") as s:
        s.set_attribute("text_len", len(text))
        result = await _post("/classify", {"text": text})
        s.set_attribute("label", result.get("label", ""))
        s.set_attribute("confidence", result.get("confidence", 0.0))
        return result


async def extract_entities(text: str) -> dict:
    """POST /ner → {entities: [...], count: N}."""
    with trace_span("modelserver.ner") as s:
        s.set_attribute("text_len", len(text))
        result = await _post("/ner", {"text": text})
        s.set_attribute("entity_count", result.get("count", 0))
        return result


async def summarize(text: str) -> dict:
    """POST /summarize → {summary, llm_used}."""
    with trace_span("modelserver.summarize") as s:
        s.set_attribute("text_len", len(text))
        result = await _post("/summarize", {"text": text})
        s.set_attribute("llm_used", result.get("llm_used", False))
        return result
