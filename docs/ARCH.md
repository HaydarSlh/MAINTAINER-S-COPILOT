# ARCH.md — Architecture & Layer Boundaries

## Layers (strict, one direction of dependency)

```
api  ->  services  ->  repositories  ->  db (ORM)
                  \->  infra (Vault, MinIO, Redis, LLM, modelserver, tracing, redaction)
domain  <- used by all layers (Pydantic models + exception hierarchy)
```

- **app/api/** — HTTP only. Routers parse/validate request, call one service method, map result to response. No SQLAlchemy, no Redis, no external calls.
- **app/services/** — business logic, transaction boundaries, cache & memory invalidation, tool-calling loop for the chatbot, RAG query orchestration.
- **app/repositories/** — SQL only. Returns domain models. No HTTP exceptions, no cache writes.
- **app/domain/** — Pydantic domain models (distinct from SQLAlchemy ORM) and the domain exception hierarchy (`AppError`, `NotFound`, `PermissionDenied`, `ValidationError`).
- **app/infra/** — adapters for every external system: Vault (secrets), MinIO (blobs), Redis (short-term memory), LLM (Gemini + Grok fallback), modelserver client, OpenTelemetry tracing, redaction filter.

## Service topology

```
Browser / host page
    └── widget iframe (React, Vite bundle, port 8080)
            └── POST /chat  (SSE stream)
                    │
            ┌───────▼────────┐       ┌──────────────────┐
            │  FastAPI (8000) │──────▶│  modelserver(8001)│
            │  app/           │       │  DistilBERT       │
            └──┬──────┬───┬──┘       └──────────────────┘
               │      │   │
          ┌────▼─┐ ┌──▼─┐ ▼
          │  PG  │ │Redis│ MinIO
          │+pgvec│ │     │ (model weights, eval reports)
          └──────┘ └─────┘
               │
           Vault (secrets)
           Jaeger (traces, port 16686)

Chatbot UI (Streamlit, port 8501) → same FastAPI /chat endpoint
```

## Request → trace mapping

Every user message produces a root span `chat.handle_message`. Child spans:
- `rag.retrieve` — hybrid BM25+dense retrieval + cross-encoder rerank
- `tool.<name>` — one span per tool call in the loop (max 5 rounds)
- `llm.call` — each Gemini/Grok invocation with provider, model, token counts
- `memory.read` / `memory.write` — Redis and pgvector operations

Traces are exported via OTLP to Jaeger at `http://jaeger:4317`. View at `http://localhost:16686`.

## Refuse-to-boot guards

Enforced in `app/main.py` startup event:

| Guard | Condition | Behaviour |
|-------|-----------|-----------|
| Vault unreachable | `read_secret()` raises on startup | `sys.exit(1)` with message |
| JWT secret missing | Vault returns empty `jwt_secret` | `sys.exit(1)` |
| Eval threshold = 0 | Any threshold in `eval_thresholds.yaml` is 0 or missing | `sys.exit(1)` |
| Weights SHA mismatch | `modelserver` `verify_weights()` fails | modelserver container exits; compose restarts |
| DB unreachable | `alembic upgrade head` fails in migrate container | api container never starts (depends_on) |
