# Maintainer's Copilot — AIE Week 7

An authenticated chatbot an open-source maintainer talks to when triaging issues.
It classifies issues (bug / feature / docs / question) with a fine-tuned encoder
compared against classical-ML and LLM baselines, extracts entities, summarizes
threads, and answers questions via advanced RAG over the project's docs and
resolved issues. It carries memory across conversations and is embeddable as a
standalone React widget. Golden-set evals fail CI on regression.

> Solo project. Five days. Scope is fixed by the brief — nothing added.

## Quick start

```bash
cp .env.example .env          # then fill in VAULT_DEV_ROOT_TOKEN
docker-compose up             # comes up cleanly from a fresh clone
```

`migrate` runs `alembic upgrade head` and exits before `api` boots.
`api` refuses to boot if Vault is unreachable, classifier weights are
missing / SHA-mismatched, tracing is misconfigured, or any eval threshold is 0.

## Compose services

| Service       | Role |
|---------------|------|
| `api`         | FastAPI: auth, chat, memory, RAG orchestration, widget config |
| `chatbot`     | Streamlit: auth UI, admin config, memory inspector, full chat |
| `widget`      | Static server for the built React widget bundle + `/widget.js` |
| `modelserver` | FastAPI inference: classifier, NER, summarizer |
| `host`        | nginx serving the demo host app that embeds the widget |
| `migrate`     | Alembic entrypoint, runs migrations, exits |
| `db`          | postgres:16 + pgvector |
| `redis`       | redis:7 — short-term memory + cache |
| `minio`       | blob: model artifacts, eval reports, training plots, chunk snapshots |
| `vault`       | hashicorp/vault (dev mode) — every secret resolves here at startup |

## Architecture (layers — the grade)

```
app/api/          HTTP only. No SQLAlchemy / Redis / external systems.
app/services/     Business logic, transaction boundaries, cache/memory invalidation.
app/repositories/ SQL only. No HTTP errors. No cache invalidation.
app/domain/       Pydantic domain models + domain exception hierarchy.
app/infra/        Adapters: Vault, MinIO, Redis, LLM, modelserver, tracing, redaction.
```

## Documentation

- [docs/ARCH.md](docs/ARCH.md) — layers, data flow, service boundaries
- [docs/DECISIONS.md](docs/DECISIONS.md) — every decision backed by a number
- [docs/RUNBOOK.md](docs/RUNBOOK.md) — operate the stack, failure modes
- [docs/EVALS.md](docs/EVALS.md) — golden sets, metrics, CI gates
- [docs/SECURITY.md](docs/SECURITY.md) — redaction patterns, secrets, origin allowlisting

## Submission

Tag: `v0.1.0-week7`
