"""LLM tool: extract code-shaped entities from issue text."""

from __future__ import annotations

SCHEMA = {
    "name": "extract_entities",
    "description": (
        "Extract code-shaped entities from issue text: exception types, function/class "
        "names, file paths, version strings, GitHub issue references, decorators. "
        "Use this to identify the technical entities mentioned in an issue."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The issue text to extract entities from.",
            }
        },
        "required": ["text"],
    },
}


async def run(text: str) -> dict:
    """Returns {entities: [{text, label, start, end}], count}."""
    from app.infra.modelserver_client import extract_entities
    return await extract_entities(text)
