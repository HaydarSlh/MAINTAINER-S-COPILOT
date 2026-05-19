# SECURITY.md — Redaction, Secrets, Origin Allowlisting

> Purpose: defend the redaction pattern list, document the secrets policy, and
> describe origin allowlisting. A redaction test proves the redaction works.

## Redaction patterns (defended list)
The redaction layer (`app/infra/redaction.py`) runs before ANY log line, trace
span, or memory write leaves the service boundary. Patterns target what
realistically appears in issue text:

| Pattern | Why it shows up in issues / why it must not be logged |
|---------|--------------------------------------------------------|
| `sk-` / provider API keys | Users paste LLM keys in repro snippets |
| GitHub tokens (`ghp_`, `gho_`, `github_pat_`) | Pasted stack traces / CI logs |
| Bearer / Authorization headers | Copied curl commands |
| Email addresses | PII in issue authorship / logs |
| AWS-style keys (`AKIA…`) | Pasted env dumps |
| Generic high-entropy secrets | Catch-all _(TODO: tune)_ |

_(TODO: finalize and justify each pattern.)_

### Redaction test (mandatory)
`tests/test_redaction.py` asserts a message containing a fake API key never
appears unredacted in logs, traces, or memory.

## Secrets policy
- Every secret resolves from Vault at startup.
- `.env` holds only the Vault root token + ports.
- `grep -ri 'sk-' app/` and `grep -ri 'password' app/` return zero matches
  outside Vault-reading code.
- App refuses to boot if Vault is unreachable.

## Origin allowlisting (production practice)
- CORS allowlist enforced from the widget's `allowed_origins` DB field, not a
  hardcoded env var.
- Embed route sets `Content-Security-Policy: frame-ancestors …` matching the
  widget's allowed origins. Unallowed parents are blocked by the browser.
