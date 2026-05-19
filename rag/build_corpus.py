"""Assemble the RAG corpus + run the preprocessing pipeline.

Corpus = the project's docs + a held-out slice of resolved issues with
maintainer answers (these held-out issues do NOT appear in classifier
training). A real preprocessing pipeline cleans/normalizes the text; choices
are defended in DECISIONS.md.
"""

# TODO: build() -> normalized documents with metadata for filtering
