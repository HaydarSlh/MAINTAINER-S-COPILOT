"""POST /ner — extract code-shaped entities from issue text.

Returns entities (exception types, identifiers, file paths, version strings,
GitHub issue refs, decorators). Backed by pipelines/ner.py.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from modelserver.pipelines.ner import extract

router = APIRouter()


class NERRequest(BaseModel):
    """Request body for the /ner endpoint."""
    text: str = Field(..., min_length=1, max_length=32_000)


class EntityOut(BaseModel):
    """A single entity extracted by the NER pipeline, serialized for the API response."""
    text: str
    label: str
    start: int
    end: int


class NERResponse(BaseModel):
    """NER endpoint response containing the entity list and total count."""
    entities: list[EntityOut]
    count: int


@router.post("/ner", response_model=NERResponse, summary="Extract code entities from issue text")
def ner(req: NERRequest) -> NERResponse:
    """Run the NER pipeline on the request text and return extracted entities."""
    try:
        entities = extract(req.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"NER pipeline error: {exc}") from exc

    return NERResponse(
        entities=[EntityOut(text=e.text, label=e.label, start=e.start, end=e.end) for e in entities],
        count=len(entities),
    )
