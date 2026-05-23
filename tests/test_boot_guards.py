"""Refuse-to-boot guard tests.

Tests the guard functions directly (not create_app) so they run offline
without a live Vault. The module-level `app = create_app()` in app.main
runs at import time, so we test the individual guard functions in isolation.
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parents[1]
_THRESHOLDS_PATH = _REPO / "eval_thresholds.yaml"


def _load_thresholds() -> dict:
    with open(_THRESHOLDS_PATH) as f:
        return yaml.safe_load(f)


# Pre-import vault with Vault mocked so app.main module-level create_app()
# doesn't fail when this test file is collected.
import app.infra.vault as _vault_mod
_vault_mod.is_reachable  # ensure it's importable


# ── Zero-threshold guard ──────────────────────────────────────────────────────

def test_refuses_boot_on_zero_eval_threshold(tmp_path):
    """_guard_eval_thresholds() must raise RuntimeError if any threshold is 0."""
    # Import the guard function directly — it does not call Vault.
    from app.main import _guard_eval_thresholds

    bad_thresholds = _load_thresholds()
    bad_thresholds["classification"]["macro_f1_min"] = 0
    bad_file = tmp_path / "eval_thresholds.yaml"
    with open(bad_file, "w") as f:
        yaml.dump(bad_thresholds, f)

    import app.main as main_mod
    original = main_mod._THRESHOLDS_PATH
    try:
        main_mod._THRESHOLDS_PATH = bad_file
        with pytest.raises(RuntimeError, match="zero"):
            _guard_eval_thresholds()
    finally:
        main_mod._THRESHOLDS_PATH = original


def test_committed_thresholds_are_all_nonzero():
    """The committed eval_thresholds.yaml must have no zero values."""
    thresholds = _load_thresholds()

    def _walk(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                _walk(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, (int, float)):
            assert obj != 0, f"Threshold {path!r} is zero in eval_thresholds.yaml"

    _walk(thresholds)


# ── Vault guard ───────────────────────────────────────────────────────────────

def test_refuses_boot_when_vault_unreachable():
    """_guard_vault() must raise RuntimeError when Vault is unreachable."""
    from app.main import _guard_vault
    # Patch at the call site — app.main imports is_reachable directly
    with patch("app.main.is_reachable", return_value=False):
        with pytest.raises(RuntimeError, match="[Vv]ault"):
            _guard_vault()


def test_boot_proceeds_when_vault_reachable():
    """_guard_vault() must not raise when Vault responds."""
    from app.main import _guard_vault
    with patch("app.main.is_reachable", return_value=True):
        _guard_vault()  # should not raise
