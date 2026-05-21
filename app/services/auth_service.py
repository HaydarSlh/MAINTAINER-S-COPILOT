"""Auth + authorization business logic.

JWT signing key resolves from Vault at startup. Two roles: user / admin.
Role changes write an audit row. bcrypt for password hashing.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.domain.enums import Role
from app.domain.exceptions import NotFoundError, PermissionDenied, ValidationError
from app.domain.models import User

_JWT_ALGORITHM = "HS256"
_JWT_EXPIRE_HOURS = 24


def _jwt_secret() -> str:
    try:
        from app.infra.vault import read_secret
        secret = read_secret("secret/data/llm").get("jwt_secret", "")
        if secret:
            return secret
    except Exception:
        pass
    secret = os.environ.get("JWT_SECRET", "")
    if not secret:
        raise RuntimeError("JWT_SECRET not configured — set in Vault at secret/data/llm or env")
    return secret


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def issue_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
        "iat": now,
        "exp": now + timedelta(hours=_JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises PermissionDenied on any failure."""
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise PermissionDenied("Token expired")
    except jwt.InvalidTokenError as exc:
        raise PermissionDenied(f"Invalid token: {exc}")


async def register(email: str, password: str) -> tuple[User, str]:
    """Create a new user. Returns (user, token). Raises ValidationError if email taken."""
    from app.db.session import get_session
    from app.repositories import user_repo

    if not email or "@" not in email:
        raise ValidationError("Invalid email address")
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters")

    async with get_session() as session:
        async with session.begin():
            existing = await user_repo.get_by_email(session, email)
            if existing:
                raise ValidationError("Email already registered")
            hashed = hash_password(password)
            user = await user_repo.create(session, email=email, hashed_password=hashed)

    token = issue_token(user)
    return user, token


async def authenticate(email: str, password: str) -> tuple[User, str]:
    """Verify credentials. Returns (user, token). Raises PermissionDenied on failure."""
    from app.db.session import get_session
    from app.repositories import user_repo

    async with get_session() as session:
        row = await user_repo.get_by_email(session, email)

    if row is None or not verify_password(password, row.hashed_password):
        raise PermissionDenied("Invalid email or password")
    if not row.is_active:
        raise PermissionDenied("Account is disabled")

    user = User(id=str(row.id), email=row.email, role=row.role)
    token = issue_token(user)
    return user, token


async def change_role(actor: User, target_user_id: str, new_role: Role) -> User:
    """Admin-only role change. Writes an audit row."""
    if actor.role != Role.ADMIN:
        raise PermissionDenied("Only admins can change roles")

    from app.db.session import get_session
    from app.repositories import audit_repo, user_repo

    async with get_session() as session:
        async with session.begin():
            updated = await user_repo.set_role(session, target_user_id, new_role)
            await audit_repo.append(
                session,
                actor_id=actor.id,
                action="auth.role_change",
                target_type="user",
                target_id=target_user_id,
                detail={"new_role": new_role.value},
            )
    return updated
