"""The MANDATORY redaction test.

Per the brief: a test asserts that a message containing a fake API key never
appears unredacted in logs, traces, OR memory. This runs in CI on every push.
"""

import pytest
from app.infra.redaction import redact, redact_dict


# ── Fake keys (safe to commit — these are test fixtures, not real secrets) ────

_FAKE_OPENAI     = "sk-abcdefghijklmnopqrstuvwxyz123456"
_FAKE_GOOGLE     = "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ12345678"
_FAKE_GROK       = "gsk_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_FAKE_GITHUB_GHP = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789"
_FAKE_GITHUB_PAT = "github_pat_" + "A" * 82
_FAKE_AWS        = "AKIAIOSFODNN7EXAMPLE"
_FAKE_BEARER     = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
_FAKE_EMAIL      = "user@example.com"
_FAKE_CONN_STR   = "postgresql://user:secretpassword@localhost:5432/db"


@pytest.mark.parametrize("text,marker", [
    (_FAKE_OPENAI,     "sk-"),
    (_FAKE_GOOGLE,     "AIzaSy"),
    (_FAKE_GITHUB_GHP, "ghp_"),
    (_FAKE_AWS,        "AKIA"),
    (_FAKE_EMAIL,      "@example.com"),
    (_FAKE_CONN_STR,   "secretpassword"),
])
def test_fake_key_never_appears_unredacted(text, marker):
    result = redact(text)
    assert marker not in result, (
        f"Redaction failed: marker {marker!r} still present in output: {result!r}"
    )
    assert "[REDACTED" in result, f"No redaction marker in output: {result!r}"


def test_grok_key_redacted():
    result = redact(f"key={_FAKE_GROK}")
    assert "gsk_" not in result


def test_bearer_token_redacted():
    result = redact(_FAKE_BEARER)
    assert "eyJhbGci" not in result
    assert "Authorization" in result  # header name preserved


def test_redact_dict_recurses():
    d = {
        "message": f"here is my key: {_FAKE_OPENAI}",
        "nested": {"token": _FAKE_GITHUB_GHP},
        "list_field": [_FAKE_EMAIL, "plain text"],
        "number": 42,
    }
    result = redact_dict(d)
    assert "sk-" not in result["message"]
    assert "ghp_" not in result["nested"]["token"]
    assert "@example.com" not in result["list_field"][0]
    assert result["list_field"][1] == "plain text"
    assert result["number"] == 42


def test_redact_non_string_passthrough():
    assert redact(None) is None
    assert redact(42) == 42
    assert redact(3.14) == 3.14


def test_normal_text_unchanged():
    text = "How do I use field_validator in Pydantic V2?"
    assert redact(text) == text
