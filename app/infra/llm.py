"""LLM provider adapter — Gemini primary, Grok backup.

The chatbot is ONE tool-calling LLM. This adapter wraps both providers,
tries Gemini first, falls back to Grok (xAI) if Gemini exhausts retries.
API keys come from Vault (never from env in production).
Provider/model choice recorded in DECISIONS.md D12.

Every call is wrapped in a trace span with model name, token counts, latency,
and redacted inputs/outputs.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

from app.infra.tracing import span as trace_span

# ── Model IDs ─────────────────────────────────────────────────────────────────
GEMINI_MODEL  = "gemini-2.5-flash"
GROK_MODEL    = "grok-3-mini"

# Transient error codes that warrant a retry / fallback
_TRANSIENT = ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "overloaded")

_MAX_RETRIES = 3   # per provider before falling back


@dataclass
class LLMResponse:
    content: str
    provider: str          # "gemini" or "claude"
    model: str
    input_tokens: int  = 0
    output_tokens: int = 0
    tool_calls: list[dict] = field(default_factory=list)


# ── Key resolution ─────────────────────────────────────────────────────────────

def _gemini_key() -> str:
    try:
        from app.infra.vault import read_secret
        key = read_secret("secret/data/llm").get("api_key", "")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("GOOGLE_API_KEY", "")


def _grok_key() -> str:
    try:
        from app.infra.vault import read_secret
        key = read_secret("secret/data/llm").get("grok_api_key", "")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("GROK_API_KEY", "")


# ── Gemini call ────────────────────────────────────────────────────────────────

def _call_gemini(messages: list[dict], tools: list[dict] | None) -> LLMResponse:
    import google.genai as genai
    from google.genai import types as gtypes

    key = _gemini_key()
    if not key:
        raise RuntimeError("Gemini API key not available")

    client = genai.Client(api_key=key)

    # Convert OpenAI-style messages to Gemini contents
    contents = []
    system_instruction = None
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            system_instruction = content
        elif role == "assistant":
            contents.append(gtypes.Content(role="model", parts=[gtypes.Part(text=content)]))
        else:
            contents.append(gtypes.Content(role="user", parts=[gtypes.Part(text=content)]))

    config = gtypes.GenerateContentConfig(
        system_instruction=system_instruction,
    )

    # Tool declarations
    if tools:
        gemini_tools = _tools_to_gemini(tools)
        config = gtypes.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=gemini_tools,
        )

    delay = 4
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )
            tool_calls = _extract_gemini_tool_calls(resp)
            text = (resp.text or "") if not tool_calls else ""
            usage = resp.usage_metadata or {}
            return LLMResponse(
                content=text,
                provider="gemini",
                model=GEMINI_MODEL,
                input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
                output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
                tool_calls=tool_calls,
            )
        except Exception as e:
            last_exc = e
            msg = str(e)
            is_transient = any(code in msg for code in _TRANSIENT)
            if is_transient and attempt < _MAX_RETRIES - 1:
                time.sleep(delay)
                delay = min(delay * 2, 30)
            else:
                break

    raise RuntimeError(f"Gemini failed after {_MAX_RETRIES} attempts: {last_exc}") from last_exc


def _tools_to_gemini(tools: list[dict]) -> list:
    """Convert OpenAI-style tool schemas to Gemini FunctionDeclaration list."""
    from google.genai import types as gtypes
    declarations = []
    for t in tools:
        fn = t.get("function", t)
        declarations.append(gtypes.Tool(function_declarations=[
            gtypes.FunctionDeclaration(
                name=fn["name"],
                description=fn.get("description", ""),
                parameters=fn.get("parameters", {}),
            )
        ]))
    return declarations


def _extract_gemini_tool_calls(resp) -> list[dict]:
    calls = []
    for part in (resp.candidates or [{}])[0].content.parts if resp.candidates else []:
        if hasattr(part, "function_call") and part.function_call:
            calls.append({
                "name": part.function_call.name,
                "arguments": dict(part.function_call.args or {}),
            })
    return calls


# ── Grok call (OpenAI-compatible) ─────────────────────────────────────────────

def _call_grok(messages: list[dict], tools: list[dict] | None) -> LLMResponse:
    from openai import OpenAI

    key = _grok_key()
    if not key:
        raise RuntimeError("Grok API key not available")

    client = OpenAI(api_key=key, base_url="https://api.x.ai/v1")

    kwargs: dict[str, Any] = dict(
        model=GROK_MODEL,
        max_tokens=2048,
        messages=messages,
    )
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    delay = 4
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = client.chat.completions.create(**kwargs)
            msg = resp.choices[0].message
            text = msg.content or ""
            tool_calls = []
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    import json
                    tool_calls.append({
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments or "{}"),
                    })
            return LLMResponse(
                content=text,
                provider="grok",
                model=GROK_MODEL,
                input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
                output_tokens=resp.usage.completion_tokens if resp.usage else 0,
                tool_calls=tool_calls,
            )
        except Exception as e:
            last_exc = e
            msg_str = str(e)
            is_transient = any(code in msg_str for code in _TRANSIENT)
            if is_transient and attempt < _MAX_RETRIES - 1:
                time.sleep(delay)
                delay = min(delay * 2, 30)
            else:
                break

    raise RuntimeError(f"Grok failed after {_MAX_RETRIES} attempts: {last_exc}") from last_exc


# ── Public interface ───────────────────────────────────────────────────────────

def chat(messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
    """Send messages to the LLM. Gemini primary, Claude Haiku backup.

    Args:
        messages: OpenAI-style message list with role/content dicts.
                  System message (role="system") is handled by both providers.
        tools:    OpenAI-style tool/function definitions. Optional.

    Returns:
        LLMResponse with content, provider, token counts, and any tool_calls.
    """
    with trace_span("llm.chat") as s:
        s.set_attribute("llm.tools_count", len(tools) if tools else 0)
        s.set_attribute("llm.messages_count", len(messages))

        # Try Gemini first
        gemini_err: Exception | None = None
        if _gemini_key():
            try:
                t0 = time.monotonic()
                result = _call_gemini(messages, tools)
                latency_ms = int((time.monotonic() - t0) * 1000)
                s.set_attribute("llm.provider", result.provider)
                s.set_attribute("llm.model", result.model)
                s.set_attribute("llm.input_tokens", result.input_tokens)
                s.set_attribute("llm.output_tokens", result.output_tokens)
                s.set_attribute("llm.latency_ms", latency_ms)
                return result
            except Exception as e:
                gemini_err = e
                s.set_attribute("llm.gemini_error", str(e)[:200])

        # Fall back to Grok
        if _grok_key():
            try:
                t0 = time.monotonic()
                result = _call_grok(messages, tools)
                latency_ms = int((time.monotonic() - t0) * 1000)
                s.set_attribute("llm.provider", result.provider)
                s.set_attribute("llm.model", result.model)
                s.set_attribute("llm.input_tokens", result.input_tokens)
                s.set_attribute("llm.output_tokens", result.output_tokens)
                s.set_attribute("llm.latency_ms", latency_ms)
                s.set_attribute("llm.fallback_used", True)
                return result
            except Exception as e:
                raise RuntimeError(
                    f"Both LLM providers failed. Gemini: {gemini_err}. Grok: {e}"
                ) from e

        raise RuntimeError(
            "No LLM API keys available. Set GOOGLE_API_KEY or GROK_API_KEY, "
            "or bootstrap Vault with secret/llm."
        )
