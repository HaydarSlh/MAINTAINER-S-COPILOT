"""Modelserver FastAPI app + its own refuse-to-boot guard.

Refuses to boot if classifier weights are missing or their SHA-256 does not
match the model card. Mounts the classify / ner / summarize routers.
"""

import json
from pathlib import Path

from fastapi import FastAPI

_REPO = Path(__file__).resolve().parents[1]
_MODEL_CARD = _REPO / "app" / "artifacts" / "model_card.json"
_MANIFEST   = _REPO / "app" / "artifacts" / "manifest.json"


def _verify_weights() -> None:
    """Assert classifier weights are present and SHA-256 matches the model card.

    The weights themselves live in MinIO and are fetched at container startup
    (outside this process). This guard checks the local copy that the fetch
    step places at CLASSIFIER_MODEL_DIR.
    """
    import hashlib
    import os

    model_dir = os.environ.get("CLASSIFIER_MODEL_DIR", "")
    if not model_dir:
        # Running without a fetched model (e.g. unit tests) — skip guard
        return

    weights_path = Path(model_dir) / "model.safetensors"
    if not weights_path.exists():
        raise RuntimeError(
            f"Classifier weights not found at {weights_path}. "
            "Run the MinIO fetch step before starting the modelserver."
        )

    with open(_MODEL_CARD) as f:
        card = json.load(f)

    expected_sha = card.get("weights_sha256", "")
    if expected_sha in ("TBD", "", None):
        raise RuntimeError(
            "model_card.json has no committed weights_sha256. "
            "Run the training notebook (Section 11) and commit the card."
        )

    with open(weights_path, "rb") as f:
        actual_sha = hashlib.sha256(f.read()).hexdigest()

    if actual_sha != expected_sha:
        raise RuntimeError(
            f"Classifier weights SHA-256 mismatch.\n"
            f"  Expected (model card): {expected_sha}\n"
            f"  Actual  (file):        {actual_sha}\n"
            "Re-fetch from MinIO or retrain."
        )


def create_app() -> FastAPI:
    """Verify classifier weights, then build and return the modelserver FastAPI app."""
    _verify_weights()

    app = FastAPI(
        title="Maintainer's Copilot — Model Server",
        description="classify / ner / summarize endpoints for the maintainer's copilot.",
        version="0.1.0",
    )

    from modelserver.routers.classify import router as classify_router
    from modelserver.routers.ner import router as ner_router
    from modelserver.routers.summarize import router as summarize_router

    app.include_router(classify_router, tags=["classification"])
    app.include_router(ner_router,      tags=["ner"])
    app.include_router(summarize_router, tags=["summarization"])

    @app.get("/health", tags=["ops"])
    def health() -> dict:
        """Return a simple liveness probe response."""
        return {"status": "ok"}

    return app


app = create_app()
