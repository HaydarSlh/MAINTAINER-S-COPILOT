"""SQLAlchemy ORM models — the persisted tables.

Distinct from app/domain Pydantic models on purpose. Repositories map between
the two. Tables sketched here for Day 1; columns finalized via Alembic
migrations as features land. Includes pgvector columns for long-term memory
and the RAG index, and the audit-log table required by the brief.
"""

# TODO: UserORM (fastapi-users compatible) — id, email, hashed_password, role
# TODO: ConversationORM, MessageORM
# TODO: MemoryORM — long-term memory, pgvector embedding column
# TODO: RagChunkORM — corpus chunks, pgvector embedding, metadata for filtering
# TODO: WidgetORM — widget_id, allowed_origins, theme, greeting, enabled_tools
# TODO: AuditLogORM — actor, action, target, timestamp
#       (role changes, memory writes, widget config changes, conv deletions)
