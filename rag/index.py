"""Build the retrieval index.

Embeds chunks and writes them to pgvector (vs Qdrant decided in DECISIONS.md
D10), including the sparse index for hybrid retrieval and the metadata used
for filtering. Run as a build/offline job, not at request time.
"""

# TODO: build_index() -> populate pgvector + sparse index
