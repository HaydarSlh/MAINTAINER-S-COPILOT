"""Redaction layer — runs before ANYTHING leaves the service boundary.

Every log line, trace span attribute, and memory write is passed through
redact() before leaving the process. Patterns are defended in SECURITY.md.
A dedicated test (tests/test_redaction.py) asserts fake keys never appear
unredacted in logs, traces, or memory.
"""

from __future__ import annotations

import re

# ── Pattern registry ──────────────────────────────────────────────────────────
# Each tuple: (compiled pattern, replacement string)
# Order matters — more specific patterns before general ones.

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # OpenAI / generic sk- keys
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "[REDACTED:API_KEY]"),
    # Google AI / Gemini keys (AIza prefix, 39 chars total)
    (re.compile(r"\bAIza[A-Za-z0-9_\-]{35}\b"), "[REDACTED:GOOGLE_KEY]"),
    # Anthropic keys
    (re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{40,}\b"), "[REDACTED:ANTHROPIC_KEY]"),
    # GitHub tokens: classic (ghp_), OAuth (gho_), fine-grained (github_pat_)
    (re.compile(r"\bgh[po]_[A-Za-z0-9]{36,}\b"), "[REDACTED:GITHUB_TOKEN]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{82}\b"), "[REDACTED:GITHUB_TOKEN]"),
    # AWS access key IDs
    (re.compile(r"\bAKIA[A-Z0-9]{16}\b"), "[REDACTED:AWS_KEY]"),
    # JWT Bearer tokens in Authorization headers
    (re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9\-._~+/]+=*"), r"\1[REDACTED:BEARER]"),
    # Vault tokens (s. prefix, 26 chars)
    (re.compile(r"\bs\.[A-Za-z0-9]{24}\b"), "[REDACTED:VAULT_TOKEN]"),
    # Passwords in connection strings: ://user:PASSWORD@host
    (re.compile(r"(://[^:@/]+:)[^@/]+(@)"), r"\1[REDACTED:PASSWORD]\2"),
    # Email addresses (in logs / memory)
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[REDACTED:EMAIL]"),
    # High-entropy catch-all: 40+ hex chars (SHA hashes, raw tokens)
    (re.compile(r"\b[0-9a-f]{40,}\b"), "[REDACTED:HIGH_ENTROPY]"),
]


def redact(text: str) -> str:
    """Return *text* with every configured secret pattern replaced.

    Safe to call on None or non-string — returns the value unchanged.
    """
    if not isinstance(text, str):
        return text
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact_dict(d: dict) -> dict:
    """Recursively redact all string values in a dict (for span attributes)."""
    out = {}
    for k, v in d.items():
        if isinstance(v, str):
            out[k] = redact(v)
        elif isinstance(v, dict):
            out[k] = redact_dict(v)
        elif isinstance(v, list):
            out[k] = [redact(i) if isinstance(i, str) else i for i in v]
        else:
            out[k] = v
    return out
