"""LLM tool: summarize an issue thread."""

from __future__ import annotations

SCHEMA = {
    "name": "summarize_issue",
    "description": (
        "Summarize a GitHub issue thread into 2-4 sentences covering: what the reporter "
        "found/asked, the root cause or key technical detail, and the current status. "
        "Use this when a maintainer needs a quick overview of a long issue thread."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The full issue thread text (title + body + comments).",
            }
        },
        "required": ["text"],
    },
}


async def run(text: str) -> dict:
    """Returns {summary, llm_used}."""
    from app.infra.modelserver_client import summarize
    return await summarize(text)
