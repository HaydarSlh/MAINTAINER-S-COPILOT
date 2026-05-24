"""Chat orchestration — single tool-calling LLM, NOT multi-agent.

Flow per turn:
  1. Load system prompt from prompts/chatbot_system.md
  2. Assemble context: short-term Redis state + top-k long-term memories
  3. Persist user message
  4. Call LLM with tool schemas
  5. Execute any tool calls (catch ToolFailure, degrade gracefully)
  6. If tools were called, send results back to LLM for final answer
  7. Persist assistant message
  8. Update short-term state
  9. Yield text tokens via async generator (SSE streaming)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import AsyncIterator

from app.domain.exceptions import ToolFailure
from app.domain.models import User
from app.infra.tracing import span as trace_span

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "chatbot_system.md"
_MAX_TOOL_ROUNDS = 5   # guard against infinite tool loops

# All tool modules — schemas for LLM, run() for execution
from app.services.tools import (
    classify_tool,
    ner_tool,
    rag_tool,
    summarize_tool,
    write_memory_tool,
)

_TOOLS: dict[str, object] = {
    "classify_issue": classify_tool,
    "extract_entities": ner_tool,
    "search_docs": rag_tool,
    "summarize_issue": summarize_tool,
    "write_memory": write_memory_tool,
}

_TOOL_SCHEMAS = [
    {"type": "function", "function": t.SCHEMA}
    for t in _TOOLS.values()
]


def _load_system_prompt() -> str:
    """Read the chatbot system prompt from disk."""
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _build_messages(
    system: str,
    history: list[dict],
    memory_context: str,
    user_text: str,
) -> list[dict]:
    """Assemble the full message list for the LLM from system prompt, memory, history, and user input."""
    messages: list[dict] = [{"role": "system", "content": system}]
    if memory_context:
        messages.append({
            "role": "system",
            "content": f"Relevant memories from past sessions:\n{memory_context}",
        })
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    return messages


async def _run_tool(name: str, arguments: dict, user_id: str) -> str:
    """Dispatch a tool call by name and return its JSON-serialized result."""
    module = _TOOLS.get(name)
    if module is None:
        raise ToolFailure(f"Unknown tool: {name}")
    try:
        if name == "write_memory":
            result = await module.run(user_id=user_id, **arguments)
        else:
            result = await module.run(**arguments)
        return json.dumps(result, ensure_ascii=False)
    except ToolFailure:
        raise
    except Exception as exc:
        raise ToolFailure(f"Tool {name} failed: {exc}") from exc


async def handle_message(
    user: User,
    conversation_id: str | None,
    text: str,
) -> AsyncIterator[str]:
    """Process one user turn. Yields text chunks for SSE streaming.

    Creates a new conversation if conversation_id is None.
    """
    from app.db.session import get_session
    from app.infra import llm
    from app.repositories import conversation_repo
    from app.services import memory_service

    with trace_span("chat.handle_message") as root_span:
        root_span.set_attribute("chat.user_id", user.id)

        # ── 1. Conversation setup ─────────────────────────────────────────────
        async with get_session() as session:
            async with session.begin():
                if conversation_id is None:
                    conv = await conversation_repo.create_conversation(
                        session, user_id=user.id
                    )
                    conversation_id = str(conv.id)
                else:
                    conv = await conversation_repo.get_conversation(session, conversation_id)
                    if conv is None:
                        from app.domain.exceptions import NotFoundError
                        raise NotFoundError(f"Conversation {conversation_id} not found")

                await conversation_repo.append_message(
                    session, conversation_id=conversation_id,
                    role="user", content=text,
                )

        # ── 2. Load context ───────────────────────────────────────────────────
        system_prompt = _load_system_prompt()

        short_term = await memory_service.get_short_term(conversation_id) or {}
        history: list[dict] = short_term.get("history", [])

        memories = await memory_service.recall(user.id, text, k=3)
        memory_context = "\n".join(f"- {m.content}" for m in memories) if memories else ""

        messages = _build_messages(system_prompt, history, memory_context, text)

        # ── 3. Tool-calling loop ──────────────────────────────────────────────
        final_text = ""
        for _round in range(_MAX_TOOL_ROUNDS):
            with trace_span("chat.llm_call") as llm_span:
                llm_span.set_attribute("chat.round", _round)
                response = llm.chat(messages, tools=_TOOL_SCHEMAS)

            if not response.tool_calls:
                final_text = response.content
                break

            # Append assistant message with tool_calls metadata
            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": response.tool_calls,
            })

            # Execute each tool call
            for call in response.tool_calls:
                tool_name = call["name"]
                tool_args = call.get("arguments", {})
                with trace_span(f"chat.tool.{tool_name}") as ts:
                    try:
                        tool_result = await _run_tool(tool_name, tool_args, user.id)
                        ts.set_attribute("tool.success", True)
                    except ToolFailure as exc:
                        tool_result = json.dumps({"error": str(exc)})
                        ts.set_attribute("tool.success", False)
                        ts.set_attribute("tool.error", str(exc))

                messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": tool_result,
                })

            # After tool results, call without tools to force a full text answer.
            # Passing tools=None prevents Gemini from calling another tool instead
            # of writing the answer, which was causing one-sentence responses.
            messages.append({
                "role": "user",
                "content": (
                    "Now write your full answer based on the tool results above. "
                    "Write at least 4-6 paragraphs. Explain every entity/finding in detail, "
                    "include code examples, explain root causes, and end with next steps."
                ),
            })
            with trace_span("chat.llm_final") as final_span:
                final_span.set_attribute("chat.round", _round)
                final_response = llm.chat(messages, tools=None)
            final_text = final_response.content
            break
        else:
            # Exceeded max rounds — ask LLM for final answer without tools
            messages.append({
                "role": "user",
                "content": "Please provide your final answer based on the tool results above.",
            })
            response = llm.chat(messages)
            final_text = response.content

        # ── 4. Persist assistant reply + update short-term state ─────────────
        async with get_session() as session:
            async with session.begin():
                await conversation_repo.append_message(
                    session, conversation_id=conversation_id,
                    role="assistant", content=final_text,
                )

        new_history = list(history)
        new_history.append({"role": "user", "content": text})
        new_history.append({"role": "assistant", "content": final_text})
        # Keep last 20 messages in short-term state to avoid unbounded growth
        new_history = new_history[-20:]
        await memory_service.set_short_term(
            conversation_id,
            {"history": new_history, "conversation_id": conversation_id},
        )

        root_span.set_attribute("chat.conversation_id", conversation_id)

    # ── 5. Yield for SSE ─────────────────────────────────────────────────────
    # Yield conversation_id first, then the full text in one shot. Streaming
    # by character/word ranges risks splitting markdown markers (** [] ``)
    # across SSE events, which breaks the renderer on the client side.
    yield f"[conv:{conversation_id}]"
    if final_text:
        yield final_text
