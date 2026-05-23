"""Widget config persistence. SQL only."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm import WidgetORM
from app.domain.models import WidgetConfig


def _to_domain(row: WidgetORM) -> WidgetConfig:
    """Convert a WidgetORM row to a WidgetConfig domain model."""
    return WidgetConfig(
        widget_id=row.id,
        allowed_origins=row.allowed_origins,
        theme=row.theme,
        greeting=row.greeting,
        enabled_tools=row.enabled_tools,
    )


async def get_orm_by_id(session: AsyncSession, widget_id: str) -> WidgetORM | None:
    """Return the raw ORM row for a widget, used when the owner_id is needed."""
    return await session.get(WidgetORM, widget_id)


async def get_by_widget_id(session: AsyncSession,
                            widget_id: str) -> WidgetConfig | None:
    """Fetch an active widget config as a domain model, or None if absent/inactive."""
    row = await session.get(WidgetORM, widget_id)
    return _to_domain(row) if row and row.is_active else None


async def create(session: AsyncSession, owner_id: str,
                  allowed_origins: list[str], theme: dict,
                  greeting: str, enabled_tools: list[str]) -> WidgetConfig:
    """Insert a new widget row with a generated short ID and return the domain model."""
    widget_id = uuid.uuid4().hex[:12]
    row = WidgetORM(
        id=widget_id,
        owner_id=uuid.UUID(owner_id),
        allowed_origins=allowed_origins,
        theme=theme,
        greeting=greeting,
        enabled_tools=enabled_tools,
    )
    session.add(row)
    await session.flush()
    return _to_domain(row)


async def update(session: AsyncSession, widget_id: str, **kwargs) -> WidgetConfig:
    """Apply keyword-argument updates to a widget row and return the updated domain model."""
    row = await session.get(WidgetORM, widget_id)
    if row is None:
        raise ValueError(f"Widget {widget_id} not found")
    for key, val in kwargs.items():
        setattr(row, key, val)
    await session.flush()
    return _to_domain(row)


async def list_all(session: AsyncSession) -> list[WidgetConfig]:
    """Return all active widget configurations as domain models."""
    result = await session.execute(
        select(WidgetORM).where(WidgetORM.is_active == True)
    )
    return [_to_domain(r) for r in result.scalars().all()]
