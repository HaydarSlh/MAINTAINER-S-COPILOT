# EVALS.md — Golden Sets & CI Gates

> Purpose: document the two golden sets, the metrics, the CI gates, and the
> human-vs-judge agreement. "The evals are the grade."

## Classification golden set
- **Location:** `evals/classification/golden_set.jsonl`
- **Size:** 25 hand-curated issues, **separate from the test split**.
- **Metrics:** macro-F1, per-class F1, confusion matrix.
- **Run against:** all three models (classical / fine-tuned / LLM).

## RAG golden set
- **Location:** `evals/rag/golden_set.jsonl`
- **Size:** 25 triples (question / ideal-answer / ground-truth-chunks).
- **Metrics:** retrieval (hit@5, MRR@10) + generation (faithfulness, answer
  relevancy) via RAGAS or a frozen judge — _decided in DECISIONS.md_.
- **Human agreement:** 5 of 25 hand-labeled; report agreement with the judge.

## CI gates
- Thresholds committed in [`eval_thresholds.yaml`](../eval_thresholds.yaml).
- Both suites run on every push. `eval_report.json` written every run,
  stored in MinIO, diffed against the previous green build.
- Regression below threshold (or beyond `regression_tolerance`) blocks merge.
- api refuses to boot if any threshold is 0/disabled.

## Results log
(TODO: append each run's headline numbers here as the week progresses.)
