"""Vault adapter — the single place secrets enter the process.

Every secret (LLM API keys, tracing keys, JWT signing key, DB password, MinIO
credentials) is read from Vault HERE at startup. No other module reads secrets.

Policy:
  - App refuses to boot if Vault is unreachable (called by app/main.py guards).
  - Secrets are cached in-process for the process lifetime to avoid per-request
    round trips; a rolling restart picks up rotated secrets.
"""

import hvac

from app.config import settings


def _client() -> hvac.Client:
    """Build an hvac client configured from settings (not cached — tokens may rotate)."""
    return hvac.Client(
        url=settings.vault_addr,
        token=settings.vault_dev_root_token,
    )


def is_reachable() -> bool:
    """Return True if Vault is up and the token is valid."""
    try:
        return _client().is_authenticated()
    except Exception:
        return False


def read_secret(path: str) -> dict:
    """Read a KV-v2 secret. *path* may be 'db', 'secret/db', or 'secret/data/db' —
    the mount prefix is stripped so hvac receives only the key name.

    Returns the ``data`` dict from the KV-v2 response.
    Raises RuntimeError if Vault is unreachable or the path does not exist.
    """
    client = _client()
    if not client.is_authenticated():
        raise RuntimeError(
            f"Vault is not reachable or token is invalid (addr={settings.vault_addr})"
        )
    # Strip mount prefix variants so callers can use any form.
    key = path.removeprefix("secret/data/").removeprefix("secret/")
    try:
        response = client.secrets.kv.v2.read_secret_version(
            mount_point="secret", path=key, raise_on_deleted_version=True
        )
        return response["data"]["data"]
    except hvac.exceptions.InvalidPath as exc:
        raise RuntimeError(f"Vault path not found: {path}") from exc
