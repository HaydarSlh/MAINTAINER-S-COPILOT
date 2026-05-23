"""Memory business logic — short-term (Redis) + long-term (pgvector).

Short-term: conversation state stored in Redis with a 30-minute TTL.
Long-term: written ONLY via the explicit write_memory tool (no auto-writes).
Every long-term write also appends an audit-log row.
recall() supports cross-conversation memory retrieval via pgvector similarity.
"""

from __future__ import annotations

from app.domain.enums import MemoryType
from app.domain.models import MemoryRecord
from app.infra import redis_client


# ── Short-term (Redis) ────────────────────────────────────────────────────────

async def get_short_term(conversation_id: str) -> dict | None:
    """Return conversation state dict or None if TTL has expired."""
    return await redis_client.get_conversation_state(conversation_id)


async def set_short_term(conversation_id: str, state: dict,
                          ttl: int = redis_client.SHORT_TERM_TTL_SECONDS) -> None:
    """Persist conversation state. TTL justified in DECISIONS.md D13."""
    await redis_client.set_conversation_state(conversation_id, state, ttl=ttl)


async def clear_short_term(conversation_id: str) -> None:
    """Evict the short-term Redis state for a conversation."""
    await redis_client.delete_conversation_state(conversation_id)


# ── Long-term (pgvector) ──────────────────────────────────────────────────────

async def write_long_term(user_id: str, content: str,
                           memory_type: MemoryType,
                           actor_id: str | None = None) -> MemoryRecord:
    """Write a memory record and append an audit-log row.

    Called ONLY from write_memory_tool — never auto-written.
    """
    from app.db.session import get_session
    from app.repositories import memory_repo, audit_repo
    from rag.embed import embed_query

    embedding = embed_query(content).tolist()

    async with get_session() as session:
        async with session.begin():
            record = await memory_repo.insert_memory(
                session, user_id=user_id,
                memory_type=memory_type,
                content=content,
                embedding=embedding,
            )
            await audit_repo.append(
                session,
                actor_id=actor_id or user_id,
                action="memory.write",
                target_type="memory",
                target_id=record.id,
                detail={"memory_type": memory_type.value, "content_len": len(content)},
            )
    return record


async def recall(user_id: str, query: str, k: int = 5) -> list[MemoryRecord]:
    """Retrieve the k most semantically similar memories for cross-conversation recall."""
    from app.db.session import get_session
    from app.repositories import memory_repo
    from rag.embed import embed_query

    embedding = embed_query(query).tolist()

    async with get_session() as session:
        return await memory_repo.search(session, user_id=user_id,
                                         query_embedding=embedding, k=k)


async def list_memories(user_id: str) -> list[MemoryRecord]:
    """List all long-term memories for a user (for Streamlit memory inspector)."""
    from app.db.session import get_session
    from app.repositories import memory_repo

    async with get_session() as session:
        return await memory_repo.list_for_user(session, user_id=user_id)
