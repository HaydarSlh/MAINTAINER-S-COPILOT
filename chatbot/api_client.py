"""Thin HTTP client to the FastAPI api service.

All Streamlit pages call this module — zero business logic here, just HTTP.
API base URL is read from the API_BASE_URL env var (default: http://api:8000).
"""

from __future__ import annotations

import os
from typing import Iterator

import httpx

API_BASE = os.environ.get("API_BASE_URL", "http://api:8000")
_TIMEOUT = 30.0


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Auth ──────────────────────────────────────────────────────────────────────

def register(email: str, password: str) -> dict:
    """Returns {access_token, token_type, user} or raises on failure."""
    r = httpx.post(
        f"{API_BASE}/auth/register",
        json={"email": email, "password": password},
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def login(email: str, password: str) -> dict:
    """Returns {access_token, token_type, user} or raises on failure."""
    r = httpx.post(
        f"{API_BASE}/auth/login",
        json={"email": email, "password": password},
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def get_me(token: str) -> dict:
    r = httpx.get(f"{API_BASE}/auth/me", headers=_headers(token), timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


# ── Chat (streaming) ──────────────────────────────────────────────────────────

def chat_stream(
    token: str,
    text: str,
    conversation_id: str | None = None,
) -> Iterator[str]:
    """Yield SSE data chunks from POST /chat.

    First chunk is always [conv:<id>] — caller should strip and store it.
    Final chunk is [DONE] — caller should stop rendering.
    """
    payload: dict = {"text": text}
    if conversation_id:
        payload["conversation_id"] = conversation_id

    with httpx.stream(
        "POST",
        f"{API_BASE}/chat",
        json=payload,
        headers={**_headers(token), "Accept": "text/event-stream"},
        timeout=60.0,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line.startswith("data: "):
                yield line[6:]


# ── Memory ────────────────────────────────────────────────────────────────────

def get_memories(token: str) -> list[dict]:
    r = httpx.get(f"{API_BASE}/memory", headers=_headers(token), timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


def delete_memory(token: str, memory_id: str) -> None:
    r = httpx.delete(
        f"{API_BASE}/memory/{memory_id}",
        headers=_headers(token),
        timeout=_TIMEOUT,
    )
    r.raise_for_status()


def get_audit_log(token: str, limit: int = 100) -> list[dict]:
    r = httpx.get(
        f"{API_BASE}/memory/audit",
        params={"limit": limit},
        headers=_headers(token),
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


# ── Widgets ───────────────────────────────────────────────────────────────────

def list_widgets(token: str) -> list[dict]:
    r = httpx.get(f"{API_BASE}/widgets", headers=_headers(token), timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


def create_widget(token: str, payload: dict) -> dict:
    r = httpx.post(
        f"{API_BASE}/widgets",
        json=payload,
        headers=_headers(token),
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def update_widget(token: str, widget_id: str, payload: dict) -> dict:
    r = httpx.put(
        f"{API_BASE}/widgets/{widget_id}",
        json=payload,
        headers=_headers(token),
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def get_snippet(token: str, widget_id: str) -> str:
    r = httpx.get(
        f"{API_BASE}/widgets/{widget_id}/snippet",
        headers=_headers(token),
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["snippet"]
