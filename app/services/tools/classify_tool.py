"""LLM tool: classify an issue into bug/feature/docs/question."""

from __future__ import annotations

from app.domain.exceptions import DomainError


SCHEMA = {
    "name": "classify_issue",
    "description": (
        "Classify a GitHub issue into one of: bug, feature, docs, question. "
        "Use this when the maintainer pastes or describes an issue and wants to know its type."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The full issue text (title + body).",
            }
        },
        "required": ["text"],
    },
}


async def run(text: str) -> dict:
    """Returns {label, confidence, fallback_used}."""
    from app.services.classification_service import classify_issue
    result = await classify_issue(text)
    return {
        "label": result.label.value,
        "confidence": round(result.confidence, 4),
        "fallback_used": result.fallback_used,
    }
