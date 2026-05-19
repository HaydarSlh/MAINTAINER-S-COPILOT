"""SQLAlchemy declarative base. All ORM models inherit from `Base`.

Schema is owned exclusively by Alembic migrations (the `migrate` container);
nothing here creates tables at runtime.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
