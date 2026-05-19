# ARCH.md — Architecture & Layer Boundaries

> Purpose: describe the layered architecture and the data flow. The boundary
> will be checked live on Friday by being asked to add a new endpoint or tool.

## Layers (strict, one direction of dependency)

```
api  ->  services  ->  repositories  ->  db (ORM)
                  \->  infra (Vault, MinIO, Redis, LLM, modelserver, tracing, redaction)
domain  <- used by all layers (Pydantic models + exception hierarchy)
```

- **app/api/** — HTTP only. Routers parse/validate, call a service, map result.
  No SQLAlchemy, no Redis, no external calls here.
- **app/services/** — business logic, transaction boundaries, cache & memory
  invalidation, tool orchestration for the chatbot.
- **app/repositories/** — SQL only. Returns domain models. No HTTP errors,
  no cache invalidation.
- **app/domain/** — Pydantic domain models (distinct from SQLAlchemy ORM) and
  the domain exception hierarchy.
- **app/infra/** — adapters for every external system + the redaction layer.

## Request → trace mapping

(TODO: fill in once chatbot is built) A conversation is a trace tree rooted at
the user message; every LLM call, tool call, and RAG retrieval is a span.

## Service topology

(TODO: diagram of api / modelserver / chatbot / widget / host and shared DB.)

## Refuse-to-boot guards

(TODO: enumerate the startup assertions implemented in `app/main.py`.)
