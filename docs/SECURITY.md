# SECURITY.md — Redaction, Secrets, Origin Allowlisting

## Redaction patterns

The redaction layer (`app/infra/redaction.py`) runs before ANY log line, trace span, or memory write leaves the service boundary. Every string passing through the LLM, tool responses, and user messages is filtered.

| Pattern | Regex anchor | Why it appears in issue text |
|---------|-------------|------------------------------|
| Grok API keys | `gsk_[A-Za-z0-9\-_]{40,}` | Users paste xAI keys in repro snippets |
| OpenAI-style keys | `sk-[A-Za-z0-9]{20,}` | pasted LLM keys in CI config examples |
| GitHub tokens | `ghp_`, `gho_`, `github_pat_` | pasted from stack traces / CI logs |
| Bearer / Authorization headers | `Bearer\s+[A-Za-z0-9\-._~+/]{20,}` | copied curl commands in bug reports |
| Email addresses | RFC-5322 local@domain | PII in issue authorship and logs |
| AWS access keys | `AKIA[0-9A-Z]{16}` | pasted env dumps |
| Generic high-entropy tokens | `[A-Za-z0-9+/]{40,}={0,2}` (base64) | catch-all for unknown secrets |

### Redaction test

`tests/test_redaction.py` asserts that a message containing a synthetic API key in each pattern above is never returned unredacted from `redact()`. The test is mandatory — CI blocks if it fails.

### What is NOT redacted

- Pydantic class names, stack traces, version strings — these are the corpus of the tool and must pass through.
- User issue text body — redaction runs only on outbound paths (logs, traces, memory writes), not on inbound storage. Issues are stored as-submitted in the DB.

## Secrets policy

- Every secret resolves from **Vault KV-v2** at startup via `app/infra/vault.py`.
- `.env` holds **only** `VAULT_DEV_ROOT_TOKEN` and port mappings. No API keys in `.env`.
- `grep -ri 'sk-' app/` and `grep -ri 'password' app/` return zero matches outside Vault-reading code.
- The API refuses to boot (`sys.exit(1)`) if Vault is unreachable or returns an empty JWT secret.
- Secret paths: `secret/data/llm` (api_key, grok_api_key, jwt_secret, github_token), `secret/data/db` (password), `secret/data/minio` (access_key, secret_key), `secret/data/tracing` (endpoint).

## Origin allowlisting

Widget embeds are restricted at two layers:

1. **CORS** (`app/api/routers/embed.py`): `Access-Control-Allow-Origin` on `/embed/config/{id}` is set to the widget's `allowed_origins` list from the DB — not a wildcard, not an env var.
2. **CSP** (`app/api/routers/embed.py`): `Content-Security-Policy: frame-ancestors <origins>` is injected on the config response so browsers refuse to render the iframe on unlisted parent domains.

Origins are validated on write (`app/services/widget_service.py`): must start with `http://` or `https://`, no trailing slash enforcement, no wildcards allowed. Every origin change is written to the audit log.

## JWT policy

- Algorithm: HS256, 24-hour expiry.
- Secret: 32+ character random string stored in Vault `secret/data/llm.jwt_secret`.
- No refresh tokens — users re-authenticate after 24 hours.
- `decode_token()` raises `AuthenticationError` on expired or tampered tokens; the dependency (`get_current_user`) maps this to HTTP 401.

## Audit log

Every privileged action writes a row to `audit_logs`:
- Widget create / update (origin changes)
- Role change (`change_role` — admin-only)
- Memory delete

Rows are append-only (no UPDATE/DELETE on `audit_logs`). Accessible to admins via `GET /memory/audit`.
