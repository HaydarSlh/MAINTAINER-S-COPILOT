"""Build and query the retrieval index.

Index = pgvector (dense HNSW) + BM25 (sparse, in-memory rank_bm25).
Hybrid retrieval combines both with a tuned alpha weight (DECISIONS.md D6).

Offline build:
    python -m rag.index --corpus corpus.jsonl --strategy structure

Query (used by rag_service at request time — not this module directly;
rag_service calls retrieve() after the index is built):
    from rag.index import retrieve
    chunks = retrieve("how do I use field_validator?", k=5)
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from rag.chunking import Chunk, chunk_corpus
from rag.embed import DEFAULT_MODEL, embed_query, embed_texts, get_embedder

# ── Retrieval result ───────────────────────────────────────────────────────────

@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    content: str
    score: float
    metadata: dict = field(default_factory=dict)


# ── BM25 sparse index (in-memory) ────────────────────────────────────────────

def _tokenise(text: str) -> list[str]:
    """Simple whitespace + punctuation tokeniser for BM25."""
    import re
    return re.findall(r"[a-zA-Z0-9_\.]+", text.lower())


class BM25Index:
    def __init__(self, chunks: list[Chunk]) -> None:
        from rank_bm25 import BM25Okapi
        self._chunks = chunks
        corpus = [_tokenise(c.content) for c in chunks]
        self._bm25 = BM25Okapi(corpus)

    def scores(self, query: str) -> np.ndarray:
        tokens = _tokenise(query)
        raw = self._bm25.get_scores(tokens)
        # Normalise to [0, 1]
        mx = raw.max()
        return raw / mx if mx > 0 else raw


# ── Dense vector index (pgvector) ─────────────────────────────────────────────

class DenseIndex:
    """Thin wrapper — embeds all chunks and stores vectors in pgvector.

    Falls back to an in-memory numpy index when pgvector is unreachable
    (useful for running experiments without the full compose stack).
    """

    def __init__(self, chunks: list[Chunk], model_name: str = DEFAULT_MODEL) -> None:
        self._chunks = chunks
        self._model_name = model_name
        self._vectors: np.ndarray | None = None   # set after build()

    def build(self, use_pgvector: bool = True) -> None:
        """Embed all chunks and (optionally) upsert into pgvector."""
        embedder = get_embedder(self._model_name)
        texts = [c.content for c in self._chunks]
        print(f"Embedding {len(texts)} chunks with {self._model_name} ...", file=sys.stderr)
        self._vectors = embed_texts(texts, embedder=embedder)

        if use_pgvector:
            self._upsert_pgvector()

    def _upsert_pgvector(self) -> None:
        """Write chunk embeddings into the rag_chunks table."""
        try:
            import asyncio
            asyncio.run(self._async_upsert())
        except Exception as e:
            print(f"WARNING: pgvector upsert failed ({e}); using in-memory index", file=sys.stderr)

    async def _async_upsert(self) -> None:
        import uuid
        from sqlalchemy import text
        from app.db.session import get_engine

        async with get_engine().begin() as conn:
            for i, (chunk, vec) in enumerate(zip(self._chunks, self._vectors)):
                await conn.execute(
                    text("""
                        INSERT INTO rag_chunks
                            (id, doc_id, chunk_index, content, embedding, metadata)
                        VALUES
                            (:id, :doc_id, :chunk_index, :content, :embedding, :metadata)
                        ON CONFLICT (doc_id, chunk_index) DO UPDATE
                            SET content   = EXCLUDED.content,
                                embedding = EXCLUDED.embedding,
                                metadata  = EXCLUDED.metadata
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "doc_id": chunk.doc_id,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "embedding": vec.tolist(),
                        "metadata": json.dumps(chunk.metadata),
                    }
                )
            if i % 500 == 0 and i > 0:
                print(f"  Upserted {i} chunks ...", file=sys.stderr)

    def scores(self, query_vec: np.ndarray) -> np.ndarray:
        """Cosine similarity scores (vectors are already L2-normalised)."""
        if self._vectors is None:
            raise RuntimeError("DenseIndex.build() must be called first")
        return (self._vectors @ query_vec).astype(float)


# ── Hybrid index ──────────────────────────────────────────────────────────────

class HybridIndex:
    """Combines dense and BM25 scores with a tunable alpha weight.

    final_score = alpha * dense_score + (1 - alpha) * bm25_score
    """

    def __init__(self, chunks: list[Chunk], model_name: str = DEFAULT_MODEL,
                 alpha: float = 0.6) -> None:
        self._chunks = chunks
        self.alpha = alpha
        self._dense = DenseIndex(chunks, model_name=model_name)
        self._bm25 = BM25Index(chunks)

    def build(self, use_pgvector: bool = True) -> None:
        self._dense.build(use_pgvector=use_pgvector)

    def retrieve(self, query: str, k: int = 5,
                 model_name: str = DEFAULT_MODEL) -> list[RetrievedChunk]:
        """Retrieve top-k chunks by hybrid score.

        Args:
            query:      Natural language query string.
            k:          Number of results to return.
            model_name: Embedding model (must match what was used at index time).
        """
        query_vec = embed_query(query, model_name=model_name)

        dense_scores = self._dense.scores(query_vec)
        bm25_scores = self._bm25.scores(query)

        hybrid = self.alpha * dense_scores + (1 - self.alpha) * bm25_scores
        top_k_idx = np.argsort(hybrid)[::-1][:k]

        return [
            RetrievedChunk(
                chunk_id=self._chunks[i].chunk_id,
                doc_id=self._chunks[i].doc_id,
                content=self._chunks[i].content,
                score=float(hybrid[i]),
                metadata=self._chunks[i].metadata,
            )
            for i in top_k_idx
        ]


# ── Cross-encoder reranker ─────────────────────────────────────────────────────

class CrossEncoderReranker:
    """Reranks candidates with ms-marco-MiniLM-L-6-v2 (local, CPU-fast).

    Decision: DECISIONS.md D7a.
    """

    _MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(self) -> None:
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            print(f"Loading cross-encoder: {self._MODEL} ...", file=sys.stderr)
            self._model = CrossEncoder(self._MODEL)
        return self._model

    def rerank(self, query: str, candidates: list[RetrievedChunk],
               top_k: int = 5) -> list[RetrievedChunk]:
        """Rerank candidates and return top_k."""
        if not candidates:
            return candidates
        model = self._load()
        pairs = [(query, c.content) for c in candidates]
        scores = model.predict(pairs)
        ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
        return [c for _, c in ranked[:top_k]]


# ── Query transformation ───────────────────────────────────────────────────────

def multi_query(question: str, n: int = 3) -> list[str]:
    """Generate n paraphrases of question via LLM, return all including original."""
    from app.infra.llm import chat
    prompt = (
        f"Generate {n} different phrasings of this question about the pydantic Python library. "
        f"Each phrasing should use different vocabulary but ask the same thing. "
        f"Output ONLY the questions, one per line, no numbering.\n\n"
        f"Question: {question}"
    )
    try:
        resp = chat([{"role": "user", "content": prompt}])
        variants = [l.strip() for l in (resp.content or "").split("\n") if l.strip()][:n]
        return [question] + variants
    except Exception:
        return [question]


def hyde(question: str) -> str:
    """Generate a hypothetical answer to use as the retrieval query (HyDE).

    Embeds the hypothetical answer instead of the question — the answer is
    phrased more like the corpus than the question is.
    """
    from app.infra.llm import chat
    prompt = (
        "Write a short technical answer (3-5 sentences) to the following question "
        "about the pydantic Python library, as if you were a maintainer writing "
        "documentation. Focus on technical accuracy.\n\n"
        f"Question: {question}\n\nAnswer:"
    )
    try:
        resp = chat([{"role": "user", "content": prompt}])
        return (resp.content or question).strip()
    except Exception:
        return question


def step_back(question: str) -> str:
    """Generate a more general/abstract version of the question (step-back prompting)."""
    from app.infra.llm import chat
    prompt = (
        "Rephrase the following specific technical question into a more general question "
        "about the underlying concept in pydantic. This helps find relevant background "
        "documentation.\n\n"
        f"Specific question: {question}\n\nGeneral question:"
    )
    try:
        resp = chat([{"role": "user", "content": prompt}])
        return (resp.content or question).strip()
    except Exception:
        return question


# ── Global index singleton (used by rag_service) ──────────────────────────────

_INDEX: HybridIndex | None = None
_RERANKER: CrossEncoderReranker | None = None


def get_index() -> HybridIndex:
    global _INDEX
    if _INDEX is None:
        raise RuntimeError(
            "RAG index not initialised. Call build_index() at startup "
            "or run: python -m rag.index --corpus corpus.jsonl"
        )
    return _INDEX


def get_reranker() -> CrossEncoderReranker:
    global _RERANKER
    if _RERANKER is None:
        _RERANKER = CrossEncoderReranker()
    return _RERANKER


def load_index(corpus_path: str, strategy: str = "structure",
               model_name: str = DEFAULT_MODEL, alpha: float = 0.6,
               use_pgvector: bool = True) -> HybridIndex:
    """Build and cache the global index from a corpus JSONL file."""
    global _INDEX
    print(f"Building RAG index: strategy={strategy} model={model_name} alpha={alpha}",
          file=sys.stderr)
    docs = []
    with open(corpus_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))

    chunks = chunk_corpus(docs, strategy=strategy)
    print(f"Chunks: {len(chunks)}", file=sys.stderr)

    _INDEX = HybridIndex(chunks, model_name=model_name, alpha=alpha)
    _INDEX.build(use_pgvector=use_pgvector)
    return _INDEX


def retrieve(query: str, k: int = 5, first_stage_k: int = 20,
             transform: str = "none") -> list[RetrievedChunk]:
    """Full retrieval pipeline: transform → hybrid retrieve → rerank.

    Args:
        query:         User's question.
        k:             Final number of chunks to return (after reranking).
        first_stage_k: Number of candidates for the reranker (before top-k).
        transform:     Query transformation — "none", "multi_query", "hyde", "step_back".
    """
    index = get_index()
    reranker = get_reranker()
    model_name = DEFAULT_MODEL

    # Query transformation
    if transform == "multi_query":
        queries = multi_query(query)
        # Retrieve for each variant, deduplicate by chunk_id, keep best score
        seen: dict[str, RetrievedChunk] = {}
        for q in queries:
            for r in index.retrieve(q, k=first_stage_k, model_name=model_name):
                if r.chunk_id not in seen or r.score > seen[r.chunk_id].score:
                    seen[r.chunk_id] = r
        candidates = sorted(seen.values(), key=lambda r: r.score, reverse=True)[:first_stage_k]

    elif transform == "hyde":
        hypo_answer = hyde(query)
        candidates = index.retrieve(hypo_answer, k=first_stage_k, model_name=model_name)

    elif transform == "step_back":
        abstract_q = step_back(query)
        # Merge with original to keep specificity
        orig_results = index.retrieve(query, k=first_stage_k // 2, model_name=model_name)
        back_results = index.retrieve(abstract_q, k=first_stage_k // 2, model_name=model_name)
        seen = {}
        for r in orig_results + back_results:
            if r.chunk_id not in seen or r.score > seen[r.chunk_id].score:
                seen[r.chunk_id] = r
        candidates = sorted(seen.values(), key=lambda r: r.score, reverse=True)[:first_stage_k]

    else:
        candidates = index.retrieve(query, k=first_stage_k, model_name=model_name)

    # Cross-encoder reranking
    return reranker.rerank(query, candidates, top_k=k)


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build RAG index from corpus JSONL")
    parser.add_argument("--corpus", required=True, help="Path to corpus.jsonl")
    parser.add_argument("--strategy", default="structure", choices=["structure", "naive"])
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--alpha", type=float, default=0.6)
    parser.add_argument("--no-pgvector", action="store_true")
    args = parser.parse_args()

    load_index(
        corpus_path=args.corpus,
        strategy=args.strategy,
        model_name=args.model,
        alpha=args.alpha,
        use_pgvector=not args.no_pgvector,
    )
    print("Index built successfully.")
