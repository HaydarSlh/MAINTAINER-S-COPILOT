"""Closed enumerations shared across layers.

IssueLabel is the 4-class classification target. Role drives authorization
(user vs admin). MemoryType is the long-term memory taxonomy — the brief
requires implementing at least one and defending the choice in DECISIONS.md.
"""

from enum import Enum


class IssueLabel(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    DOCS = "docs"
    QUESTION = "question"


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"


class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
