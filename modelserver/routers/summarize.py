"""POST /summarize — summarize an issue thread.

LLM-driven (Gemini 2.5 Flash via Vault). Falls back to extractive summary
when the LLM is unavailable. Backed by pipelines/summarizer.py.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from modelserver.pipelines.summarizer import summarize

router = APIRouter()


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=32_000)


class SummarizeResponse(BaseModel):
    summary: str
    llm_used: bool


@router.post("/summarize", response_model=SummarizeResponse, summary="Summarize a GitHub issue thread")
def summarize_issue(req: SummarizeRequest) -> SummarizeResponse:
    try:
        summary, llm_used = summarize(req.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Summarizer error: {exc}") from exc

    return SummarizeResponse(summary=summary, llm_used=llm_used)
