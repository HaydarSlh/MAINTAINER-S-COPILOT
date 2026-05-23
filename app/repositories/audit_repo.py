"""Audit-log persistence. SQL only. Append-only — never updated or deleted."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm import AuditLogORM


async def append(session: AsyncSession, actor_id: str | None,
                  action: str, target_type: str | None = None,
                  target_id: str | None = None,
                  detail: dict | None = None) -> AuditLogORM:
    """Insert a new audit-log row and flush without committing."""
    row = AuditLogORM(
        id=uuid.uuid4(),
        actor_id=uuid.UUID(actor_id) if actor_id else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail or {},
    )
    session.add(row)
    await session.flush()
    return row


async def list_recent(session: AsyncSession, limit: int = 100,
                       actor_id: str | None = None) -> list[AuditLogORM]:
    """Return the most recent audit-log rows, optionally filtered by actor."""
    q = select(AuditLogORM).order_by(AuditLogORM.created_at.desc()).limit(limit)
    if actor_id:
        q = q.where(AuditLogORM.actor_id == uuid.UUID(actor_id))
    result = await session.execute(q)
    return list(result.scalars().all())
