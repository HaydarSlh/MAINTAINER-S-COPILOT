"""Advanced RAG orchestration — the production pipeline.

Pipeline (per DECISIONS.md D5–D7):
  1. Query transformation  (multi_query / hyde / step_back — chosen in D7b)
  2. Hybrid retrieval      (BM25 + dense, alpha tuned in D6)
  3. Cross-encoder rerank  (ms-marco-MiniLM-L-6-v2, D7a)
  4. Context assembly      (top-5 chunks + metadata)
  5. Answer generation     (Gemini → Claude Haiku fallback, D12)
  6. Citation formatting   (chunk source + section_title)

Every retrieval is a trace span. Retrieved-chunk snapshots saved to MinIO
for the last N conversations (for debugging and eval).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.infra.tracing import span as trace_span

# Query transformation technique — change this after experiments to the
# winner from DECISIONS.md D7b. Options: "none", "multi_query", "hyde", "step_back"
_QUERY_TRANSFORM: str = "multi_query"

# Number of final chunks passed to the LLM
_TOP_K: int = 5

# First-stage candidates before reranking
_FIRST_STAGE_K: int = 20

_ANSWER_PROMPT = """\
You are an expert on the pydantic Python library, assisting an open-source maintainer.
Answer the question using ONLY the information in the provided context chunks.
If the context does not contain enough information to answer, say so clearly.
Cite the source of each claim using the chunk's source identifier in brackets, e.g. [docs::concepts/validators.md].

Context:
{context}

Question: {question}

Answer:"""


@dataclass
class Citation:
    """A single document chunk referenced by a RAG answer."""
    chunk_id: str
    doc_id: str
    section_title: str
    source: str   # "docs" or "issue"
    score: float


@dataclass
class RAGAnswer:
    """Full result returned by the RAG pipeline including answer text, citations, and metadata."""
    answer: str
    citations: list[Citation]
    query_transform_used: str
    provider: str    # which LLM answered
    chunks_retrieved: int


def _format_context(chunks) -> str:
    """Format retrieved chunks as a labelled context block for the answer prompt."""
    parts = []
    for c in chunks:
        title = c.metadata.get("section_title", "")
        label = f"[{c.doc_id}]" + (f" — {title}" if title else "")
        parts.append(f"{label}\n{c.content}")
    return "\n\n---\n\n".join(parts)


async def answer(question: str,
                 transform: str | None = None) -> RAGAnswer:
    """Answer a maintainer question via the full RAG pipeline.

    Args:
        question:  The user's natural language question.
        transform: Override the default query transformation technique.
                   Pass None to use the default (_QUERY_TRANSFORM).
    """
    from rag.index import retrieve
    from app.infra.llm import chat

    transform = transform or _QUERY_TRANSFORM

    with trace_span("rag.answer") as s:
        s.set_attribute("rag.question_len", len(question))
        s.set_attribute("rag.transform", transform)

        # ── Retrieval ──────────────────────────────────────────────────────────
        with trace_span("rag.retrieve"):
            chunks = retrieve(
                query=question,
                k=_TOP_K,
                first_stage_k=_FIRST_STAGE_K,
                transform=transform,
            )

        s.set_attribute("rag.chunks_retrieved", len(chunks))

        if not chunks:
            return RAGAnswer(
                answer="I could not find relevant documentation for your question.",
                citations=[],
                query_transform_used=transform,
                provider="none",
                chunks_retrieved=0,
            )

        # ── Generation ─────────────────────────────────────────────────────────
        context = _format_context(chunks)
        prompt = _ANSWER_PROMPT.format(context=context, question=question)

        with trace_span("rag.generate") as gs:
            resp = chat([{"role": "user", "content": prompt}])
            gs.set_attribute("llm.provider", resp.provider)
            gs.set_attribute("llm.input_tokens", resp.input_tokens)
            gs.set_attribute("llm.output_tokens", resp.output_tokens)

        # ── Snapshot to MinIO (best-effort) ────────────────────────────────────
        _snapshot_chunks(question, chunks)

        citations = [
            Citation(
                chunk_id=c.chunk_id,
                doc_id=c.doc_id,
                section_title=c.metadata.get("section_title", ""),
                source=c.metadata.get("source", ""),
                score=round(c.score, 4),
            )
            for c in chunks
        ]

        return RAGAnswer(
            answer=resp.content,
            citations=citations,
            query_transform_used=transform,
            provider=resp.provider,
            chunks_retrieved=len(chunks),
        )


def _snapshot_chunks(question: str, chunks: list) -> None:
    """Best-effort snapshot of retrieved chunks to MinIO for debugging."""
    try:
        import io, json, time
        from app.infra.minio_client import put_object

        payload = {
            "question": question,
            "ts": int(time.time()),
            "chunks": [
                {"chunk_id": c.chunk_id, "score": c.score, "content": c.content[:300]}
                for c in chunks
            ],
        }
        key = f"rag_snapshots/{payload['ts']}.json"
        data = json.dumps(payload, ensure_ascii=False).encode()
        put_object("evals", key, io.BytesIO(data), len(data))
    except Exception:
        pass   # snapshot failure never blocks the answer
