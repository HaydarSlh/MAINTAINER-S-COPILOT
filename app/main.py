"""FastAPI application factory + the REFUSE-TO-BOOT startup guards.

Per the brief, `api` must refuse to boot if:
  - Vault is unreachable,
  - classifier weights are missing,
  - the weights' SHA-256 does not match the model card,
  - the tracing backend is misconfigured,
  - any committed eval threshold is set to zero / disabled.

This module wires the app together but holds NO business logic — it mounts
routers (app/api), installs the single domain-exception handler, and runs the
startup assertions. Everything else lives in the proper layer.
"""

from fastapi import FastAPI


def _run_boot_guards() -> None:
    """Assert every refuse-to-boot precondition. Raises -> container exits."""
    # TODO: vault reachable (app/infra/vault.py)
    # TODO: classifier weights present + SHA-256 matches model card
    # TODO: tracing backend configured (app/infra/tracing.py)
    # TODO: eval_thresholds.yaml has no zero/disabled threshold
    ...


def create_app() -> FastAPI:
    app = FastAPI(title="Maintainer's Copilot API")
    _run_boot_guards()

    # TODO: install single exception handler (app/api/errors.py)
    # TODO: install CORS from widget allowed_origins (DB-driven, not env)
    # TODO: mount routers from app/api/routers/
    # TODO: init tracing so every request is a trace root

    return app


app = create_app()
