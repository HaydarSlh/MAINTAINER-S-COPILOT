# RUNBOOK.md — Operating the Stack

## Bring-up (fresh clone)

```bash
cp .env.example .env          # set VAULT_DEV_ROOT_TOKEN=dev-root-token
docker-compose up
```

Boot order enforced by `depends_on` + healthchecks:
`vault` → `db` / `redis` / `minio` → `migrate` (runs alembic, exits) → `modelserver` → `api` → `chatbot` / `widget` / `host`

## Secret seeding (first boot only)

```bash
# Bootstrap all secrets into Vault dev server
bash scripts/vault_bootstrap.sh

# Or manually:
docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN=dev-root-token \
  maintainers-copilot-vault-1 \
  vault kv put secret/llm \
    api_key="<GEMINI_KEY>" \
    grok_api_key="<GROK_KEY>" \
    jwt_secret="<RANDOM_32_CHARS>"
```

## Offline jobs

| Job | Command | Output |
|-----|---------|--------|
| Fetch issues + build splits | `python -m ml.data.fetch_issues` | `data/splits/` |
| Fine-tune DistilBERT | Run `notebooks/training.ipynb` (Colab T4) | weights in MinIO `models/` |
| Build RAG corpus | `python -m rag.build_corpus --out corpus.jsonl` | `corpus.jsonl` |
| Build RAG index (pgvector) | `python -m rag.index --corpus corpus.jsonl` | pgvector `rag_chunks` table |
| Run classification eval | `python -m evals.classification.run_eval --model-dir model_cache --no-gate` | `eval_report_classification.json` |
| Run RAG eval | `python -m evals.rag.run_eval --corpus corpus.jsonl --no-generation` | `eval_report_rag.json` |

## Fetch model weights from MinIO

```bash
python -c "
from modelserver.pipelines.classifier import _get_model_and_tokenizer
# Or use mc CLI:
# mc cp local/models/distilbert/ model_cache/ --recursive
"
```

## Failure modes

| Failure | Symptom | Response |
|---------|---------|----------|
| **Vault unreachable at boot** | api container exits with `Vault unreachable` | Check `docker-compose logs vault`; ensure `VAULT_DEV_ROOT_TOKEN` in `.env` matches |
| **Vault 403 permission denied** | `read_secret()` raises 403 | Token mismatch — re-check token: `docker inspect vault \| grep VAULT_DEV_ROOT_TOKEN` |
| **Weights SHA mismatch** | modelserver exits at startup | Re-fetch weights from MinIO or retrain and commit new SHA to `app/artifacts/model_card.json` |
| **Eval threshold = 0** | api refuses to boot | All thresholds in `eval_thresholds.yaml` must be non-zero |
| **Classifier endpoint down** | Chat responds with tool-failure message | modelserver health: `curl localhost:8001/health`; `docker-compose restart modelserver` |
| **Redis unreachable** | Short-term memory silently disabled | Check `docker-compose logs redis`; conversation still works, history lost |
| **pgvector table missing** | RAG queries fail | Re-run migrate: `docker-compose run --rm migrate` |
| **MinIO bucket missing** | Eval upload fails (WARNING only) | `mc mb local/evals local/models`; eval still writes locally |

## Ports

| Service | Port |
|---------|------|
| FastAPI | 8000 |
| Streamlit chatbot | 8501 |
| Widget (nginx) | 8080 |
| Demo host page | 8090 |
| modelserver | 8001 |
| Vault UI | 8200 |
| MinIO console | 9001 |
| Jaeger UI | 16686 |
| PostgreSQL | 5432 |
| Redis | 6379 |
