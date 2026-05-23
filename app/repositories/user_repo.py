"""User persistence. SQL only — no HTTP errors, no cache invalidation."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm import UserORM
from app.domain.enums import Role
from app.domain.models import User


def _to_domain(row: UserORM) -> User:
    """Convert a UserORM row to a User domain model."""
    return User(id=str(row.id), email=row.email, role=row.role)


async def get_by_id(session: AsyncSession, user_id: str) -> User | None:
    """Fetch a user by UUID string, returning None if not found."""
    row = await session.get(UserORM, uuid.UUID(user_id))
    return _to_domain(row) if row else None


async def get_by_email(session: AsyncSession, email: str) -> UserORM | None:
    """Returns the raw ORM row so auth_service can verify the hashed password."""
    result = await session.execute(select(UserORM).where(UserORM.email == email))
    return result.scalar_one_or_none()


async def create(session: AsyncSession, email: str, hashed_password: str,
                 role: Role = Role.USER) -> User:
    """Insert a new user row and return the domain model."""
    row = UserORM(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hashed_password,
        role=role,
    )
    session.add(row)
    await session.flush()
    return _to_domain(row)


async def set_role(session: AsyncSession, user_id: str, role: Role) -> User:
    """Update a user's role and return the updated domain model."""
    row = await session.get(UserORM, uuid.UUID(user_id))
    if row is None:
        raise ValueError(f"User {user_id} not found")
    row.role = role
    await session.flush()
    return _to_domain(row)
