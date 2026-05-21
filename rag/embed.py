"""Embedding model for the RAG corpus.

Two candidates compared on the golden set (DECISIONS.md D4):
  - all-MiniLM-L6-v2        (384-dim, fast, general purpose)
  - multi-qa-mpnet-base-dot-v1 (768-dim, trained for Q→passage retrieval)

The chosen model is used for both corpus indexing and query embedding at
retrieval time. Model is loaded once and cached for the process lifetime.

Usage:
    from rag.embed import get_embedder, embed_texts
    embedder = get_embedder("multi-qa-mpnet-base-dot-v1")
    vectors = embed_texts(["text one", "text two"], embedder)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import numpy as np

# Default model — override to "all-MiniLM-L6-v2" for the comparison run
DEFAULT_MODEL = "multi-qa-mpnet-base-dot-v1"

# Batch size for encoding — keeps GPU/CPU memory bounded
_BATCH_SIZE = 64


class Embedder(Protocol):
    """Minimal interface any embedding backend must satisfy."""
    def encode(self, texts: list[str], batch_size: int = 64,
               show_progress_bar: bool = False) -> np.ndarray: ...
    @property
    def get_sentence_embedding_dimension(self) -> int: ...


@lru_cache(maxsize=2)   # cache both candidate models during comparison
def get_embedder(model_name: str = DEFAULT_MODEL):
    """Load and cache a SentenceTransformer model.

    Args:
        model_name: HuggingFace model id or local path.
    Returns:
        SentenceTransformer instance.
    """
    from sentence_transformers import SentenceTransformer
    print(f"Loading embedding model: {model_name} ...")
    model = SentenceTransformer(model_name)
    return model


def embed_texts(texts: list[str], embedder=None,
                model_name: str = DEFAULT_MODEL) -> np.ndarray:
    """Embed a list of texts.

    Args:
        texts:      List of strings to embed.
        embedder:   Pre-loaded embedder instance (optional; loads DEFAULT_MODEL if None).
        model_name: Used only if embedder is None.

    Returns:
        numpy array of shape (len(texts), embedding_dim), float32.
    """
    if embedder is None:
        embedder = get_embedder(model_name)
    vectors = embedder.encode(
        texts,
        batch_size=_BATCH_SIZE,
        show_progress_bar=len(texts) > 100,
        normalize_embeddings=True,   # cosine similarity via dot product
    )
    return vectors.astype(np.float32)


def embed_query(query: str, embedder=None,
                model_name: str = DEFAULT_MODEL) -> np.ndarray:
    """Embed a single query string. Returns 1-D float32 array."""
    vecs = embed_texts([query], embedder=embedder, model_name=model_name)
    return vecs[0]


def embedding_dim(model_name: str = DEFAULT_MODEL) -> int:
    """Return the embedding dimension for the given model."""
    return get_embedder(model_name).get_sentence_embedding_dimension()
