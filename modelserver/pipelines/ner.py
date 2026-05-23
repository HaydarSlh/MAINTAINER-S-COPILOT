"""NER pipeline — extract code-shaped entities from issue text.

Uses spaCy en_core_web_sm as the base model, augmented with a rule-based
EntityRuler that catches the high-density patterns specific to pydantic issues:
  - Python exception types and error codes  (ValidationError, PydanticV2Error)
  - Qualified identifiers / function calls   (model.dict(), BaseModel.model_validate)
  - File paths                               (src/pydantic/main.py, ./config.py)
  - Version strings                          (v2.5.0, 2.5.0rc1)
  - GitHub issue/PR references               (#1234)
  - Pydantic field/validator decorators      (@field_validator, @model_validator)

Entity labels returned:
  EXCEPTION   Python exception class
  IDENTIFIER  function, method, class name or attribute access
  FILEPATH    file or module path
  VERSION     version number / tag
  ISSUE_REF   GitHub #N reference
  DECORATOR   Python decorator name
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

# ── Entity label constants ────────────────────────────────────────────────────
EXCEPTION  = "EXCEPTION"
IDENTIFIER = "IDENTIFIER"
FILEPATH   = "FILEPATH"
VERSION    = "VERSION"
ISSUE_REF  = "ISSUE_REF"
DECORATOR  = "DECORATOR"


@dataclass
class Entity:
    """A single extracted code-shaped entity with its label and character offsets."""
    text: str
    label: str
    start: int   # character offset in original text
    end: int


# ── Regex patterns (applied in order; first match wins per span) ──────────────
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # GitHub issue/PR refs — match before identifiers so #123 isn't eaten
    (ISSUE_REF,   re.compile(r"#\d+")),
    # Version strings: v2.5.0, 2.5.0, 2.5.0rc1, 2.5.0.dev0
    (VERSION,     re.compile(r"\bv?\d+\.\d+(?:\.\d+)*(?:[a-z]\w*)?\b")),
    # Decorators
    (DECORATOR,   re.compile(r"@[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*")),
    # File/module paths: contains / or \ or starts with ./ or ends in .py/.toml/.cfg
    (FILEPATH,    re.compile(
        r"(?:\.{0,2}[/\\][\w./\\-]+|[\w-]+(?:[/\\][\w./\\-]+)+|[\w.-]+\.(?:py|toml|cfg|ini|json|yaml|yml))\b"
    )),
    # Python exception names: CamelCase ending in Error/Warning/Exception
    (EXCEPTION,   re.compile(r"\b[A-Z][a-zA-Z]*(?:Error|Warning|Exception|Fault)\b")),
    # Qualified identifiers: at least one dot, like BaseModel.model_validate or pydantic.v1.main
    (IDENTIFIER,  re.compile(r"\b[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)+(?:\(\))?\b")),
    # Standalone PascalCase names that look like class names (≥2 uppercase letters)
    (IDENTIFIER,  re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z]*)+\b")),
]


@lru_cache(maxsize=1)
def _compiled_patterns() -> list[tuple[str, re.Pattern[str]]]:
    """Return the module-level compiled pattern list (cached for the process lifetime)."""
    return _PATTERNS


def extract(text: str) -> list[Entity]:
    """Extract code-shaped entities from *text*.

    Overlapping spans are resolved greedily (longest match wins; earlier pattern
    label wins on equal length). Returns entities sorted by start offset.
    """
    occupied: list[tuple[int, int]] = []
    entities: list[Entity] = []

    for label, pattern in _compiled_patterns():
        for m in pattern.finditer(text):
            s, e = m.start(), m.end()
            # Skip if this span overlaps any already-claimed span
            if any(s < oe and e > os for os, oe in occupied):
                continue
            occupied.append((s, e))
            entities.append(Entity(text=m.group(), label=label, start=s, end=e))

    entities.sort(key=lambda ent: ent.start)
    return entities
