"""Alembic migration environment.

The DB URL is built HERE at runtime from the password resolved out of Vault —
never from a committed file (secrets policy). Run by the `migrate` compose
container: `alembic upgrade head`, then it exits before `api` boots.
"""

# TODO: resolve DB password via app.infra.vault, build URL, run migrations
# TODO: target_metadata = app.db.base.Base.metadata (for autogenerate)
