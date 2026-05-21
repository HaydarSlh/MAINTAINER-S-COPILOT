"""Long-term memory persistence — pgvector similarity search. SQL only."""

from __future__ import annotations

import uuid

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm import MemoryORM
from app.domain.enums import MemoryType
from app.domain.models import MemoryRecord


def _to_domain(row: MemoryORM) -> MemoryRecord:
    return MemoryRecord(
        id=str(row.id),
        user_id=str(row.user_id),
        type=row.memory_type,
        content=row.content,
    )


async def insert_memory(session: AsyncSession, user_id: str,
                         memory_type: MemoryType, content: str,
                         embedding: list[float]) -> MemoryRecord:
    row = MemoryORM(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        memory_type=memory_type,
        content=content,
        embedding=embedding,
    )
    session.add(row)
    await session.flush()
    return _to_domain(row)


async def search(session: AsyncSession, user_id: str,
                  query_embedding: list[float], k: int = 5) -> list[MemoryRecord]:
    """ANN cosine similarity search over this user's memory entries."""
    vec_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    result = await session.execute(
        text("""
            SELECT id, user_id, memory_type, content
            FROM memory
            WHERE user_id = :user_id
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :k
        """),
        {"user_id": user_id, "vec": vec_str, "k": k},
    )
    rows = result.fetchall()
    return [
        MemoryRecord(
            id=str(r.id),
            user_id=str(r.user_id),
            type=r.memory_type,
            content=r.content,
        )
        for r in rows
    ]


async def list_for_user(session: AsyncSession,
                         user_id: str) -> list[MemoryRecord]:
    result = await session.execute(
        select(MemoryORM)
        .where(MemoryORM.user_id == uuid.UUID(user_id))
        .order_by(MemoryORM.created_at.desc())
    )
    return [_to_domain(r) for r in result.scalars().all()]


async def delete_memory(session: AsyncSession, memory_id: str) -> None:
    row = await session.get(MemoryORM, uuid.UUID(memory_id))
    if row:
        await session.delete(row)
        await session.flush()
