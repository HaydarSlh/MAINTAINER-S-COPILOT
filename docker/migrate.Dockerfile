# Image for the `migrate` service. Runs `alembic upgrade head` then EXITS.
# `api` must not boot until this has completed (compose depends_on).

FROM python:3.11-slim
WORKDIR /srv
COPY pyproject.toml ./
# TODO: pip install "." ; COPY alembic/ alembic.ini app/ ;
#       CMD alembic upgrade head
