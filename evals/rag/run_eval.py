"""Run the RAG golden set.

Retrieval metrics (hit@5, MRR@10) + generation metrics (faithfulness, answer
relevancy) via RAGAS or a frozen judge (DECISIONS.md D11). Also reports
agreement between the judge and the 5 hand-labeled examples. Feeds
evals/report.py and the CI gate.
"""

# TODO: load golden_set.jsonl, run RAG pipeline, compute metrics + agreement
