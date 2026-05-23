"""Closed enumerations shared across layers.

IssueLabel is the 4-class classification target. Role drives authorization
(user vs admin). MemoryType is the long-term memory taxonomy — the brief
requires implementing at least one and defending the choice in DECISIONS.md.
"""

from enum import Enum


class IssueLabel(str, Enum):
    """The four target classes for GitHub issue classification."""
    BUG = "bug"
    FEATURE = "feature"
    DOCS = "docs"
    QUESTION = "question"


class Role(str, Enum):
    """Authorization role; drives admin-only route guards."""
    USER = "user"
    ADMIN = "admin"


class MemoryType(str, Enum):
    """Taxonomy for long-term memory entries (episodic, semantic, or procedural)."""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
