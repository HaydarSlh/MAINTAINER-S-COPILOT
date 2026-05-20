"""Alembic migration environment.

The DB URL is built here at runtime from the password resolved out of Vault.
The `migrate` compose container runs `alembic upgrade head` then exits; the
`api` container must not boot until that service_completed_successfully.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.db.base import Base
from app.infra.vault import read_secret

# Import all ORM models so their metadata is registered with Base
import app.db.orm  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _db_url() -> str:
    creds = read_secret("secret/db")
    user = creds["username"]
    password = creds["password"]
    return (
        f"postgresql+psycopg2://{user}:{password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _db_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
