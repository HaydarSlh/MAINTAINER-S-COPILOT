"""LLM tool: answer a maintainer question via the advanced RAG pipeline."""

from __future__ import annotations

SCHEMA = {
    "name": "search_docs",
    "description": (
        "Search the pydantic documentation and resolved issues to answer a technical "
        "question. Returns a cited answer grounded in the official docs and past "
        "maintainer responses. Use this for 'how do I...', 'why does X fail', or "
        "'what is the difference between...' questions about pydantic."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The technical question to answer.",
            },
            "transform": {
                "type": "string",
                "enum": ["none", "multi_query", "hyde", "step_back"],
                "description": "Query transformation technique. Default: multi_query.",
            },
        },
        "required": ["question"],
    },
}


async def run(question: str, transform: str = "multi_query") -> dict:
    """Returns {answer, citations: [{chunk_id, doc_id, section_title, source, score}],
    query_transform_used, provider}."""
    from app.services.rag_service import answer
    result = await answer(question, transform=transform)
    return {
        "answer": result.answer,
        "citations": [
            {
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "section_title": c.section_title,
                "source": c.source,
                "score": c.score,
            }
            for c in result.citations
        ],
        "query_transform_used": result.query_transform_used,
        "provider": result.provider,
    }
