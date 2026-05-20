# Image for the `migrate` service. Runs `alembic upgrade head` then EXITS.
# `api` must not boot until this has completed (compose depends_on + condition).

FROM python:3.11-slim
WORKDIR /srv

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir "."

COPY alembic/ alembic/
COPY alembic.ini ./
COPY app/ app/

CMD ["alembic", "upgrade", "head"]
