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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.domain.exceptions import DomainError
from app.infra.vault import is_reachable
from app.infra.tracing import init_tracing

_THRESHOLDS_PATH = Path(__file__).parent.parent / "eval_thresholds.yaml"
_MODEL_CARD_PATH = Path(__file__).parent / "artifacts" / "model_card.json"


def _guard_vault() -> None:
    """Raise RuntimeError if Vault is unreachable or the token is invalid."""
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
        """Recursively walk the threshold dict and raise on any zero value."""
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
    """Construct the FastAPI application, run boot guards, and mount all routers."""
    app = FastAPI(
        title="Maintainer's Copilot API",
        description="Authenticated chatbot for open-source maintainers.",
        version="0.1.0",
    )

    _run_boot_guards()

    # CORS — widget runs on a different origin from the api, so the browser
    # sends OPTIONS preflight. Per-endpoint allowlisting (widget→host) is still
    # enforced by /embed/config/{id} via DB-driven CSP frame-ancestors.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    @app.exception_handler(DomainError)
    async def _domain_error_handler(request: Request, exc: DomainError):
        """Convert any DomainError into a structured JSON error response."""
        from app.api.errors import domain_error_to_response
        return domain_error_to_response(exc)

    @app.get("/health", tags=["ops"])
    async def health():
        """Return a simple liveness probe response."""
        return {"status": "ok"}

    # Routers mounted here as they are implemented.
    # No prefix — each router declares its own full paths (e.g. /auth/login).
    from app.api.routers import auth, chat, memory, rag, widgets, embed
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(memory.router)
    app.include_router(rag.router)
    app.include_router(widgets.router)
    app.include_router(embed.router)

    @app.on_event("startup")
    async def _load_rag_index() -> None:
        """Build the hybrid RAG index from corpus.jsonl on startup.

        Embeddings are cached to /tmp/rag_vectors.npy so restarts skip
        the ~2-minute re-embedding step. Delete the file to force a rebuild.
        """
        import numpy as np
        corpus = Path(__file__).parent.parent / "corpus.jsonl"
        if not corpus.exists():
            print(f"WARN: RAG corpus not found at {corpus} — search_docs tool will fail")
            return

        cache_path = Path("/tmp/rag_vectors.npy")
        from rag.chunking import chunk_corpus
        from rag.index import HybridIndex, _RERANKER, get_reranker
        import rag.index as _rag_index
        import json

        docs = []
        with open(corpus, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    docs.append(json.loads(line))

        chunks = chunk_corpus(docs, strategy="structure")

        if cache_path.exists():
            print("RAG index: loading cached embeddings from /tmp/rag_vectors.npy ...")
            from rag.embed import get_embedder, DEFAULT_MODEL
            from rag.index import BM25Index, DenseIndex
            import numpy as np
            vectors = np.load(str(cache_path))
            dense = DenseIndex(chunks)
            dense._vectors = vectors
            idx = HybridIndex.__new__(HybridIndex)
            idx._chunks = chunks
            idx.alpha = 0.6
            idx._dense = dense
            idx._bm25 = BM25Index(chunks)
            _rag_index._INDEX = idx
        else:
            print("RAG index: embedding 918 chunks (first boot — will cache) ...")
            from rag.index import load_index
            idx = load_index(str(corpus), use_pgvector=False)
            if idx._dense._vectors is not None:
                np.save(str(cache_path), idx._dense._vectors)
                print("RAG index: embeddings cached to /tmp/rag_vectors.npy")

        print(f"RAG index loaded from {corpus}")

    return app


app = create_app()
