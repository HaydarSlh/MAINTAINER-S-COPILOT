"""RAG route: direct question → answer + citations.

POST /rag/query  — thin wrapper over rag_service.answer, used by eval harness
                   and available directly for debugging retrieval outside chat.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.domain.models import User

router = APIRouter(tags=["rag"])


class RAGRequest(BaseModel):
    question: str
    transform: str = "multi_query"


class Citation(BaseModel):
    chunk_id: str
    doc_id: str
    section_title: str
    source: str
    score: float


class RAGResponse(BaseModel):
    answer: str
    citations: list[Citation]
    query_transform_used: str
    provider: str
    chunks_retrieved: int


@router.post("/rag/query", response_model=RAGResponse)
async def rag_query(
    body: RAGRequest,
    _user: User = Depends(get_current_user),
) -> RAGResponse:
    from app.services.rag_service import answer

    result = await answer(body.question, transform=body.transform)
    return RAGResponse(
        answer=result.answer,
        citations=[
            Citation(
                chunk_id=c.chunk_id,
                doc_id=c.doc_id,
                section_title=c.section_title,
                source=c.source,
                score=c.score,
            )
            for c in result.citations
        ],
        query_transform_used=result.query_transform_used,
        provider=result.provider,
        chunks_retrieved=result.chunks_retrieved,
    )
