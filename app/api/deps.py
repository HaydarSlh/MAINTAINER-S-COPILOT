"""FastAPI dependencies — wiring only.

get_current_user: extracts + validates the Bearer JWT and returns a User.
require_admin: raises 403 if the authenticated user is not an admin.
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.enums import Role
from app.domain.exceptions import NotFoundError, PermissionDenied
from app.domain.models import User

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    if creds is None:
        raise PermissionDenied("No authorization header")

    from app.services.auth_service import decode_token
    payload = decode_token(creds.credentials)

    from app.db.session import get_session
    from app.repositories import user_repo

    async with get_session() as session:
        user = await user_repo.get_by_id(session, payload["sub"])

    if user is None:
        raise NotFoundError("User not found")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.ADMIN:
        raise PermissionDenied("Admin access required")
    return user
