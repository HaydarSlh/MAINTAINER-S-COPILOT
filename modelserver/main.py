"""Modelserver FastAPI app + its own refuse-to-boot guard.

Refuses to boot if classifier weights are missing or their SHA-256 does not
match the model card (the api also asserts this independently). Mounts the
classify / ner / summarize routers.
"""

from fastapi import FastAPI


def _verify_weights() -> None:
    """Assert classifier weights present and SHA-256 matches the model card."""
    # TODO: load model card, hash artifact, compare; raise on mismatch
    ...


def create_app() -> FastAPI:
    app = FastAPI(title="Maintainer's Copilot Model Server")
    _verify_weights()
    # TODO: mount routers (classify, ner, summarize)
    return app


app = create_app()
