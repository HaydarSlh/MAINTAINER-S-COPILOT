"""baseline schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-18

The Alembic baseline (Monday task). Enables the pgvector extension and creates
the core tables: users, conversations, messages, long-term memory (pgvector),
RAG chunks (pgvector + metadata), widgets, audit_log. Columns filled in as
features land — kept minimal here so the `migrate` container has a head to
upgrade to from a fresh clone.
"""

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # TODO: create_table users / conversations / messages / memory /
    #       rag_chunks / widgets / audit_log


def downgrade() -> None:
    # TODO: drop tables; intentionally do NOT drop the vector extension
    ...
