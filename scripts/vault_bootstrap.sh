#!/usr/bin/env bash
# Seed every secret into Vault dev so the stack can resolve them at startup.
# Run once after `vault` container is healthy:
#   docker-compose exec vault sh /scripts/vault_bootstrap.sh
#
# NEVER commit real values here — this is the template. Fill in your values
# via environment variables or pass them on the command line:
#   DB_PASSWORD=... MINIO_SECRET=... ./vault_bootstrap.sh
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_DEV_ROOT_TOKEN:-changeme-dev-root-token}"

export VAULT_ADDR VAULT_TOKEN

echo "→ Enabling KV-v2 secrets engine (idempotent)..."
vault secrets enable -version=2 -path=secret kv 2>/dev/null || true

echo "→ Writing secret/db ..."
vault kv put secret/db \
    username="${DB_USER:-copilot}" \
    password="${DB_PASSWORD:?DB_PASSWORD must be set}"

echo "→ Writing secret/minio ..."
vault kv put secret/minio \
    access_key="${MINIO_ACCESS_KEY:-minioadmin}" \
    secret_key="${MINIO_SECRET_KEY:?MINIO_SECRET_KEY must be set}"

echo "→ Writing secret/jwt ..."
vault kv put secret/jwt \
    signing_key="${JWT_SIGNING_KEY:?JWT_SIGNING_KEY must be set}"

echo "→ Writing secret/llm ..."
vault kv put secret/llm \
    api_key="${GOOGLE_API_KEY:?GOOGLE_API_KEY must be set}"

echo "→ Writing secret/tracing ..."
vault kv put secret/tracing \
    endpoint="${TRACING_ENDPOINT:-http://jaeger:4317}" \
    service_name="${TRACING_SERVICE_NAME:-maintainers-copilot}"

echo "✓ Vault bootstrap complete."
