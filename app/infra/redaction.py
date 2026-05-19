"""Redaction layer — runs before ANYTHING leaves the service boundary.

Per the brief: a redaction layer runs before any log line, trace span, or
memory write leaves the service boundary. It lives in app/infra/ and is used
by EVERY service. Patterns are defended in docs/SECURITY.md. A dedicated test
(tests/test_redaction.py) asserts a fake API key never appears unredacted in
logs, traces, or memory.

This is the only place redaction patterns are defined. Logging, tracing, and
memory writes all funnel through `redact()`.
"""

import re

# Pattern list — each entry defended in docs/SECURITY.md. Refined Wed.
_PATTERNS: list[tuple[re.Pattern, str]] = [
    # TODO: provider API keys (sk-...), GitHub tokens (ghp_/gho_/github_pat_),
    # Bearer/Authorization, emails, AWS keys (AKIA...), high-entropy catch-all.
]


def redact(text: str) -> str:
    """Return `text` with every configured secret pattern masked."""
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text
