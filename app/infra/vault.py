"""Vault adapter — the single place secrets enter the process.

Every secret (LLM API keys, tracing keys, JWT signing key, DB password, MinIO
credentials) is read from Vault HERE at startup. No other module reads secrets.
This is why `grep -ri 'sk-' app/` returns zero matches outside this file.

Policy:
  - App refuses to boot if Vault is unreachable (called by app/main.py guards).
  - "Vault unreachable while already running" policy is documented in RUNBOOK.md
    and enforced here (decide: cache at boot vs re-read).
"""

# TODO: hvac client from settings.vault_addr + root token
# TODO: read_secret(path) helper
# TODO: is_reachable() used by the refuse-to-boot guard


def read_secret(path: str) -> dict:
    """Resolve a secret from Vault. Raises if unreachable."""
    raise NotImplementedError
