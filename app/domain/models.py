"""Pydantic domain models — the language services and the API speak.

These are intentionally separate from SQLAlchemy ORM models (app/db/orm.py):
repositories translate ORM rows <-> these domain models so business logic never
touches the ORM directly. Stubs only for Day 1; fields filled as features land.
"""

from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import IssueLabel, MemoryType, Role


class User(BaseModel):
    """Domain model representing an authenticated user."""
    id: str
    email: str
    role: Role


class Conversation(BaseModel):
    """Domain model representing a chat conversation."""
    id: str
    user_id: str
    created_at: datetime


class Classification(BaseModel):
    """Result of the issue classification pipeline including the predicted label and confidence."""
    label: IssueLabel
    confidence: float
    fallback_used: bool = False   # True when LLM fallback fired due to low DL confidence


class MemoryRecord(BaseModel):
    """A long-term memory entry (pgvector-backed). Every write also produces
    an audit-log row — see app/domain enums + repositories/audit_repo.py."""

    id: str
    user_id: str
    type: MemoryType
    content: str


class WidgetConfig(BaseModel):
    """Public widget config keyed by widget_id. Drives CORS allowlist and the
    embed route's CSP frame-ancestors — see app/api/routers/embed.py."""

    widget_id: str
    allowed_origins: list[str]
    theme: dict
    greeting: str
    enabled_tools: list[str]
