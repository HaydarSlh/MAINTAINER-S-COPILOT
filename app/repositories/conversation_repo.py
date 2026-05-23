"""Conversation + message persistence. SQL only."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.orm import ConversationORM, MessageORM


async def create_conversation(session: AsyncSession, user_id: str,
                               widget_id: str | None = None) -> ConversationORM:
    """Insert a new conversation row and return it."""
    row = ConversationORM(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        widget_id=widget_id,
    )
    session.add(row)
    await session.flush()
    return row


async def get_conversation(session: AsyncSession,
                            conversation_id: str) -> ConversationORM | None:
    """Fetch a conversation by ID with its messages eagerly loaded."""
    return await session.get(
        ConversationORM,
        uuid.UUID(conversation_id),
        options=[selectinload(ConversationORM.messages)],
    )


async def append_message(session: AsyncSession, conversation_id: str,
                          role: str, content: str,
                          tool_calls: dict | None = None) -> MessageORM:
    """Append a new message row to an existing conversation."""
    row = MessageORM(
        id=uuid.uuid4(),
        conversation_id=uuid.UUID(conversation_id),
        role=role,
        content=content,
        tool_calls=tool_calls,
    )
    session.add(row)
    await session.flush()
    return row


async def list_for_user(session: AsyncSession,
                         user_id: str) -> list[ConversationORM]:
    """Return all conversations for a user, most recent first."""
    result = await session.execute(
        select(ConversationORM)
        .where(ConversationORM.user_id == uuid.UUID(user_id))
        .order_by(ConversationORM.created_at.desc())
    )
    return list(result.scalars().all())


async def delete(session: AsyncSession, conversation_id: str) -> None:
    """Delete a conversation and its messages (cascaded by the DB)."""
    row = await session.get(ConversationORM, uuid.UUID(conversation_id))
    if row:
        await session.delete(row)
        await session.flush()
