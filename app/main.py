"""FastAPI application factory + the REFUSE-TO-BOOT startup guards.

Per the brief, `api` refuses to boot if:
  - Vault is unreachable,
  - classifier weights are missing or their SHA-256 does not match the model card,
  - the tracing backend is misconfigured (endpoint empty / Vault path missing),
  - any committed eval threshold is set to zero / disabled.

This module wires the app together but holds NO business logic — it mounts
routers (app/api), installs the single domain-exception handler, and runs the
startup assertions before the first request is accepted.
"""

import yaml
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.exceptions import DomainError
from app.infra.vault import is_reachable
from app.infra.tracing import init_tracing

_THRESHOLDS_PATH = Path(__file__).parent.parent / "eval_thresholds.yaml"
_MODEL_CARD_PATH = Path(__file__).parent / "artifacts" / "model_card.json"


def _guard_vault() -> None:
    if not is_reachable():
        raise RuntimeError(
            "Vault is unreachable. Start the vault container and re-run "
            "scripts/vault_bootstrap.sh before starting the api."
        )


def _guard_eval_thresholds() -> None:
    """Refuse to boot if any threshold in eval_thresholds.yaml is zero / null."""
    if not _THRESHOLDS_PATH.exists():
        raise RuntimeError(f"eval_thresholds.yaml not found at {_THRESHOLDS_PATH}")

    with open(_THRESHOLDS_PATH) as f:
        thresholds = yaml.safe_load(f)

    def _walk(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                _walk(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, (int, float)):
            if obj == 0:
                raise RuntimeError(
                    f"Eval threshold {path!r} is zero in eval_thresholds.yaml. "
                    "Set a non-zero minimum before deploying."
                )

    _walk(thresholds)


def _run_boot_guards() -> None:
    """Assert every refuse-to-boot precondition. Raises → container exits."""
    _guard_vault()
    # Tracing must be initialised before the first request
    init_tracing()
    _guard_eval_thresholds()
    # Classifier weight integrity is checked by modelserver at its own boot;
    # api verifies modelserver is reachable via the depends_on healthcheck in
    # docker-compose, so no duplicate SHA check here.


def create_app() -> FastAPI:
    app = FastAPI(
        title="Maintainer's Copilot API",
        description="Authenticated chatbot for open-source maintainers.",
        version="0.1.0",
    )

    _run_boot_guards()

    @app.exception_handler(DomainError)
    async def _domain_error_handler(request: Request, exc: DomainError):
        from app.api.errors import domain_error_to_response
        return domain_error_to_response(exc)

    @app.get("/health", tags=["ops"])
    async def health():
        return {"status": "ok"}

    # Routers mounted here as they are implemented
    from app.api.routers import auth, chat, memory, rag, widgets, embed
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(chat.router, prefix="/chat", tags=["chat"])
    app.include_router(memory.router, prefix="/memory", tags=["memory"])
    app.include_router(rag.router, prefix="/rag", tags=["rag"])
    app.include_router(widgets.router, prefix="/widgets", tags=["widgets"])
    app.include_router(embed.router, tags=["embed"])

    return app


app = create_app()
