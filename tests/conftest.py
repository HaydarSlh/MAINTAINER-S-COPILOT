"""Test configuration — patches services that aren't available locally.

app/main.py calls create_app() at module level, which runs boot guards.
These guards connect to Vault (Docker internal hostname) and init tracing.
We patch them here before any test module imports app.main.
"""

from unittest.mock import patch, MagicMock

# Patch Vault + tracing before app.main is imported by any test.
# These patches stay in place for the whole test session.
_vault_patch   = patch("app.infra.vault.is_reachable", return_value=True)
_tracing_patch = patch("app.infra.tracing.init_tracing", return_value=None)

_vault_patch.start()
_tracing_patch.start()
