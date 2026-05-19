"""Async SQLAlchemy engine + session factory.

The DB password is resolved from Vault at startup (app/infra/vault.py) — it is
never read from .env or hardcoded. Only repositories use sessions; services own
the transaction boundary, the API layer never touches a session.
"""

# TODO: build async engine from Vault-resolved DB password
# TODO: async_sessionmaker + get_session() dependency for repositories


def get_engine():  # noqa: D401 - stub
    """Return the process-wide async engine (built once at startup)."""
    raise NotImplementedError
