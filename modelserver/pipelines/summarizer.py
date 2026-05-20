"""Summarization pipeline — condense an issue thread via Gemini.

LLM-driven (Gemini 2.5 Flash). The API key resolves from Vault at call time
so no secret touches this module. Falls back to a simple extractive summary
(first 3 sentences) if the LLM is unavailable, so the endpoint never hard-fails
in dev when Vault is not bootstrapped.

Decision recorded in DECISIONS.md D12.
"""

from __future__ import annotations

import os
import re
import time
from functools import lru_cache

_PROMPT = """\
You are a senior open-source maintainer reviewing a GitHub issue.
Summarize the following issue thread in 2–4 sentences. Cover:
1. What the reporter is asking or what bug they found.
2. The root cause or key technical detail (if known from the thread).
3. Current status / resolution (if any).

Be concise and technical. Do not repeat the issue title verbatim.

Issue thread:
\"\"\"
{text}
\"\"\"

Summary:"""

_MAX_INPUT_CHARS = 8000   # ~2k tokens; keeps latency low
_MAX_RETRIES = 4


def _api_key() -> str:
    """Resolve Gemini API key: Vault first, env var fallback."""
    try:
        from app.infra.vault import read_secret
        key = read_secret("secret/data/llm").get("api_key", "")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("GOOGLE_API_KEY", "")


@lru_cache(maxsize=1)
def _client():
    import google.genai as genai
    return genai.Client(api_key=_api_key())


def _extractive_fallback(text: str) -> str:
    """Return the first 3 sentences as a best-effort fallback summary."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:3])


def summarize(text: str) -> tuple[str, bool]:
    """Summarize *text* with Gemini 2.5 Flash.

    Returns:
        (summary_text, llm_used)  — llm_used is False when the extractive
        fallback was used instead (Vault/API unavailable or repeated 503s).
    """
    api_key = _api_key()
    if not api_key:
        return _extractive_fallback(text), False

    try:
        import google.genai as genai
    except ImportError:
        return _extractive_fallback(text), False

    client = genai.Client(api_key=api_key)
    prompt = _PROMPT.format(text=text[:_MAX_INPUT_CHARS])

    delay = 4
    for attempt in range(_MAX_RETRIES):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            summary = (resp.text or "").strip()
            if summary:
                return summary, True
            return _extractive_fallback(text), False
        except Exception as e:
            msg = str(e)
            is_transient = any(code in msg for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))
            if is_transient and attempt < _MAX_RETRIES - 1:
                time.sleep(delay)
                delay = min(delay * 2, 60)
            else:
                break

    return _extractive_fallback(text), False
