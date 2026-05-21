"""Redis adapter — short-term conversation state + cache.

TTL is explicit and justified here (DECISIONS.md D13):
  30 minutes — long enough to cover a focused triage session without
  leaving stale context if the maintainer closes the tab and returns the
  next day. At TTL expiry the next message starts a fresh context window;
  the user sees a "session expired" notice from the chat service.

Credentials: no password in dev (Redis default), Vault secret/redis in prod.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.config import settings

# Justified in DECISIONS.md D13
SHORT_TERM_TTL_SECONDS = 1800   # 30 minutes


@lru_cache(maxsize=1)
def _client():
    import redis.asyncio as aioredis
    return aioredis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        decode_responses=True,
    )


# ── Conversation state ────────────────────────────────────────────────────────

async def get_conversation_state(conversation_id: str) -> dict | None:
    """Return the short-term state dict for a conversation, or None if expired."""
    raw = await _client().get(f"conv:{conversation_id}")
    if raw is None:
        return None
    return json.loads(raw)


async def set_conversation_state(conversation_id: str, state: dict,
                                  ttl: int = SHORT_TERM_TTL_SECONDS) -> None:
    """Persist conversation state with an explicit TTL."""
    await _client().setex(f"conv:{conversation_id}", ttl, json.dumps(state))


async def delete_conversation_state(conversation_id: str) -> None:
    await _client().delete(f"conv:{conversation_id}")


# ── Generic cache helpers ─────────────────────────────────────────────────────

async def cache_get(key: str) -> Any | None:
    raw = await _client().get(key)
    return json.loads(raw) if raw is not None else None


async def cache_set(key: str, value: Any, ttl: int = SHORT_TERM_TTL_SECONDS) -> None:
    await _client().setex(key, ttl, json.dumps(value))


async def cache_delete(key: str) -> None:
    await _client().delete(key)


# ── Health check ──────────────────────────────────────────────────────────────

async def ping() -> bool:
    try:
        return await _client().ping()
    except Exception:
        return False
