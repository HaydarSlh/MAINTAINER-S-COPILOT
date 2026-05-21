"""Chunking strategy — structure-aware for docs, whole-document for issues.

Two strategies implemented so the golden-set comparison (DECISIONS.md D5) can
run both and report the delta:

  naive_chunks(doc)      — fixed 512-token windows, 50-token overlap (baseline)
  structure_chunks(doc)  — split docs on ## headers; issues kept whole

Both return the same Chunk datatype so the indexing pipeline is strategy-agnostic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    chunk_id: str          # "{doc_id}::{chunk_index}"
    doc_id: str
    chunk_index: int
    content: str           # text that gets embedded
    metadata: dict = field(default_factory=dict)   # inherits + adds section_title


# ── Tokenisation proxy (character-based, avoids tokenizer dependency) ─────────
# 1 token ≈ 4 characters for English technical text — good enough for chunking.
_CHARS_PER_TOKEN = 4
_NAIVE_MAX_TOKENS = 512
_NAIVE_OVERLAP_TOKENS = 50
_NAIVE_MAX_CHARS = _NAIVE_MAX_TOKENS * _CHARS_PER_TOKEN       # 2048
_NAIVE_OVERLAP_CHARS = _NAIVE_OVERLAP_TOKENS * _CHARS_PER_TOKEN  # 200

# Structure-aware: don't let any single section exceed this before hard-splitting
_STRUCT_MAX_CHARS = 3000


# ── Naive fixed-size baseline ──────────────────────────────────────────────────

def naive_chunks(doc: dict) -> list[Chunk]:
    """Split doc content into fixed-size windows with overlap.

    Args:
        doc: dict with keys doc_id, content, source, metadata (from build_corpus).
    """
    text = doc["content"]
    doc_id = doc["doc_id"]
    base_meta = dict(doc.get("metadata", {}))
    base_meta["source"] = doc.get("source", "")
    base_meta["strategy"] = "naive"

    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + _NAIVE_MAX_CHARS, len(text))
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(Chunk(
                chunk_id=f"{doc_id}::{idx}",
                doc_id=doc_id,
                chunk_index=idx,
                content=chunk_text,
                metadata={**base_meta, "chunk_index": idx},
            ))
            idx += 1
        start = end - _NAIVE_OVERLAP_CHARS   # overlap window
        if start >= len(text) - _NAIVE_OVERLAP_CHARS:
            break

    return chunks


# ── Structure-aware chunker ────────────────────────────────────────────────────

# Match ## and ### headers (not #### — too granular)
_HEADER_RE = re.compile(r"^(#{2,3})\s+(.+)$", re.MULTILINE)


def _split_on_headers(text: str) -> list[tuple[str, str]]:
    """Return list of (section_title, section_body) pairs.

    The content before the first header becomes an intro chunk with title "".
    """
    matches = list(_HEADER_RE.finditer(text))
    if not matches:
        return [("", text)]

    sections = []
    # Text before the first header
    intro = text[:matches[0].start()].strip()
    if intro:
        sections.append(("", intro))

    for i, m in enumerate(matches):
        title = m.group(2).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if body:
            sections.append((title, f"## {title}\n\n{body}"))

    return sections


def _hard_split(text: str, max_chars: int = _STRUCT_MAX_CHARS) -> list[str]:
    """Further split an oversized section at paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]

    paragraphs = re.split(r"\n\n+", text)
    parts: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars and current:
            parts.append(current.strip())
            current = para
        else:
            current = (current + "\n\n" + para).strip() if current else para
    if current:
        parts.append(current.strip())
    return parts


def structure_chunks(doc: dict) -> list[Chunk]:
    """Structure-aware chunking.

    - docs: split on ## / ### headers; hard-split oversized sections at paragraphs
    - issues: keep whole (title + body + maintainer reply is already a natural unit)

    Args:
        doc: dict with keys doc_id, content, source, metadata.
    """
    doc_id = doc["doc_id"]
    source = doc.get("source", "docs")
    base_meta = dict(doc.get("metadata", {}))
    base_meta["source"] = source
    base_meta["strategy"] = "structure"
    text = doc["content"]

    if source == "issue":
        # Whole issue is one chunk
        return [Chunk(
            chunk_id=f"{doc_id}::0",
            doc_id=doc_id,
            chunk_index=0,
            content=text,
            metadata={**base_meta, "section_title": doc.get("metadata", {}).get("title", "")},
        )]

    # Docs: split on headers then hard-split oversized sections
    sections = _split_on_headers(text)
    chunks: list[Chunk] = []
    idx = 0
    for title, body in sections:
        for part in _hard_split(body):
            if not part.strip():
                continue
            chunks.append(Chunk(
                chunk_id=f"{doc_id}::{idx}",
                doc_id=doc_id,
                chunk_index=idx,
                content=part,
                metadata={**base_meta, "section_title": title},
            ))
            idx += 1

    return chunks


# ── Batch helpers ──────────────────────────────────────────────────────────────

def chunk_corpus(docs: list[dict], strategy: str = "structure") -> list[Chunk]:
    """Chunk all documents with the given strategy.

    Args:
        docs:     list of Document dicts from build_corpus.build()
        strategy: "structure" (default) or "naive"
    """
    fn = structure_chunks if strategy == "structure" else naive_chunks
    all_chunks: list[Chunk] = []
    for doc in docs:
        all_chunks.extend(fn(doc))
    return all_chunks
