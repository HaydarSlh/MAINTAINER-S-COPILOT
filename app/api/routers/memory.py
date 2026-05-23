"""Memory routes: inspect long-term memory and audit log.

GET  /memory            — list the current user's long-term memories
GET  /memory/audit      — list recent audit log entries (admin only)
DELETE /memory/{id}     — delete a specific memory (owner or admin)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user, require_admin
from app.domain.models import MemoryRecord, User

router = APIRouter(tags=["memory"])


class AuditEntry(BaseModel):
    id: str
    actor_id: str | None
    action: str
    target_type: str | None
    target_id: str | None
    detail: dict
    created_at: str


@router.get("/memory", response_model=list[MemoryRecord])
async def list_memories(user: User = Depends(get_current_user)) -> list[MemoryRecord]:
    from app.services.memory_service import list_memories as svc_list
    return await svc_list(user.id)


@router.get("/memory/audit", response_model=list[AuditEntry])
async def list_audit(
    limit: int = 100,
    _admin: User = Depends(require_admin),
) -> list[AuditEntry]:
    from app.db.session import get_session
    from app.repositories import audit_repo

    async with get_session() as session:
        rows = await audit_repo.list_recent(session, limit=limit)

    return [
        AuditEntry(
            id=str(r.id),
            actor_id=str(r.actor_id) if r.actor_id else None,
            action=r.action,
            target_type=r.target_type,
            target_id=r.target_id,
            detail=r.detail or {},
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.delete("/memory/{memory_id}", status_code=204, response_model=None)
async def delete_memory(
    memory_id: str,
    user: User = Depends(get_current_user),
) -> None:
    from app.db.session import get_session
    from app.domain.exceptions import NotFoundError, PermissionDenied
    from app.repositories import memory_repo

    async with get_session() as session:
        async with session.begin():
            from app.db.orm import MemoryORM
            import uuid
            row = await session.get(MemoryORM, uuid.UUID(memory_id))
            if row is None:
                raise NotFoundError("Memory not found")
            if str(row.user_id) != user.id and user.role.value != "admin":
                raise PermissionDenied("Cannot delete another user's memory")
            await memory_repo.delete_memory(session, memory_id=memory_id)
