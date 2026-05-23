"""POST /classify — fine-tuned encoder issue classification.

Returns label (bug/feature/docs/question) + confidence + all class scores.
Backed by pipelines/classifier.py. This is the DEPLOYED model per DECISIONS.md D3.
"""

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from modelserver.pipelines.classifier import classify

router = APIRouter()

_MODEL_DIR = os.environ.get("CLASSIFIER_MODEL_DIR", "")


class ClassifyRequest(BaseModel):
    """Request body for the /classify endpoint."""
    text: str = Field(..., min_length=1, max_length=32_000)


class ClassifyResponse(BaseModel):
    """Classification result returned by /classify."""
    label: str
    label_id: int
    confidence: float
    all_scores: dict[str, float]


@router.post("/classify", response_model=ClassifyResponse, summary="Classify a GitHub issue")
def classify_issue(req: ClassifyRequest) -> ClassifyResponse:
    """Run the fine-tuned classifier on the request text and return label and scores."""
    if not _MODEL_DIR:
        raise HTTPException(
            status_code=503,
            detail="CLASSIFIER_MODEL_DIR not set — weights not fetched yet.",
        )
    try:
        result = classify(req.text, _MODEL_DIR)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Classifier error: {exc}") from exc

    return ClassifyResponse(
        label=result.label,
        label_id=result.label_id,
        confidence=result.confidence,
        all_scores=result.all_scores,
    )
