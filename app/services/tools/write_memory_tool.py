"""LLM tool: explicit write to long-term memory.

NO auto-writes — the LLM must deliberately call this tool. Every write
produces an audit-log row via memory_service.
"""

from __future__ import annotations

SCHEMA = {
    "name": "write_memory",
    "description": (
        "Save something to long-term memory that should be remembered across "
        "conversations. Only call this when the maintainer explicitly asks to remember "
        "something, or when a fact is clearly important for future sessions "
        "(e.g. a recurring bug pattern, a decision made, a user preference). "
        "Do NOT auto-write routine conversation details."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The information to remember.",
            },
            "memory_type": {
                "type": "string",
                "enum": ["episodic", "semantic", "procedural"],
                "description": (
                    "episodic: a specific event or conversation fact. "
                    "semantic: a general fact about the project or codebase. "
                    "procedural: a how-to or decision about process."
                ),
            },
        },
        "required": ["content", "memory_type"],
    },
}


async def run(user_id: str, content: str, memory_type: str) -> dict:
    """Write to long-term memory. Returns {memory_id, memory_type, content}."""
    from app.domain.enums import MemoryType
    from app.services.memory_service import write_long_term
    record = await write_long_term(
        user_id=user_id,
        content=content,
        memory_type=MemoryType(memory_type),
    )
    return {
        "memory_id": record.id,
        "memory_type": record.type,
        "content": record.content,
        "status": "saved",
    }
