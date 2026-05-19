"""Advanced RAG orchestration.

Beats the naive baseline (fixed chunks + pure dense). Pipeline:
  1. query transformation (technique chosen in DECISIONS.md D7),
  2. hybrid retrieval — sparse + dense with tuned weighting (D6),
  3. metadata filtering over the corpus,
  4. cross-encoder reranking over top-k,
  5. answer generation with citations.
Every retrieval is a trace span; retrieved-chunks snapshot saved to MinIO for
the last N conversations. Every off-baseline choice is backed by a golden-set
number.
"""

# TODO: answer(question, filters) -> answer + cited chunks
