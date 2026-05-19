# RUNBOOK.md — Operating the Stack

> Purpose: how to bring the stack up, seed secrets, run training/indexing/evals,
> and what happens at each failure mode.

## Bring-up (fresh clone)
```bash
cp .env.example .env          # fill VAULT_DEV_ROOT_TOKEN
docker-compose up
```
Boot order: `vault` → `db`/`redis`/`minio` → `migrate` (runs & exits) →
`modelserver` → `api` → `chatbot`/`widget`/`host`.

## Secret seeding
- `scripts/vault_bootstrap.sh` writes all secrets into Vault dev. _(TODO)_

## Offline jobs (not runtime containers)
- Fetch issues + splits: `python -m ml.data.fetch_issues` _(TODO)_
- Fine-tune: `python -m ml.train.finetune` _(TODO)_
- Build RAG index: `python -m rag.index` _(TODO)_

## Failure modes (the "Think About" scenarios)
- **Vault unreachable at boot:** api refuses to boot. _(policy: TODO)_
- **Vault unreachable while running:** _(policy: TODO — where it lives)_
- **Classifier endpoint down:** chatbot says so and falls back; does not 500.
- **Eval threshold set to 0:** api refuses to boot.
- **Weights SHA mismatch vs model card:** api refuses to boot.
