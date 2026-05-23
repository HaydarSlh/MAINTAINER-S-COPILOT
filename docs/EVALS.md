# EVALS.md — Golden Sets & CI Gates

## Classification golden set

- **Location:** `evals/classification/golden_set.jsonl`
- **Size:** 23 hand-curated issues (7 bug, 7 feature, 7 docs, 2 question), separate from the training/test split.
- **Curation:** issues selected for high human confidence (≥0.80 model confidence for bug/feature/docs; ≥0.65 for question — see DECISIONS.md D2). Question class limited to 2 due to structural ambiguity with bug.
- **Metrics:** macro-F1, per-class F1, confusion matrix.
- **Run against:** fine-tuned DistilBERT (gated) + classical TF-IDF+LR + LLM baseline (reference).
- **Command:** `python -m evals.classification.run_eval --model-dir model_cache`

### Results (2026-05-22)

| Model | Macro F1 | bug F1 | feature F1 | docs F1 | question F1 |
|-------|----------|--------|------------|---------|-------------|
| Fine-tuned DistilBERT | **1.00** | 1.00 | 1.00 | 1.00 | 1.00 |
| Classical ML (TF-IDF+LR) | 0.65 | 0.93 | 0.82 | 0.83 | 0.00 |
| LLM baseline (Gemini 2.5 Flash) | **1.00** | 1.00 | 1.00 | 1.00 | 1.00 |

## RAG golden set

- **Location:** `evals/rag/golden_set.jsonl`
- **Size:** 25 triples (question / reference_answer / relevant_doc_ids). Covers pydantic V2 concepts: validators, config, serialization, types, migration, FastAPI integration.
- **Metrics:** hit@5 (ground-truth doc in top-5 retrieved), MRR@10 (mean reciprocal rank).
- **Generation metrics:** faithfulness + answer_relevancy via RAGAS (requires live app stack; skipped in offline CI).
- **Command:** `python -m evals.rag.run_eval --corpus corpus.jsonl --no-generation`

### Results (2026-05-22)

| Strategy | Chunks | hit@5 | MRR@10 |
|----------|--------|-------|--------|
| Structure-aware (deployed) | 918 | **0.72** | **0.50** |
| Naive fixed-size baseline | 992 | 0.72 | 0.48 |

Model: `multi-qa-mpnet-base-dot-v1`, hybrid BM25+dense α=0.6, cross-encoder reranker `ms-marco-MiniLM-L-6-v2`.

## CI gates

Thresholds committed in [`eval_thresholds.yaml`](../eval_thresholds.yaml). Both suites run on every push.

| Metric | Threshold | Observed | Status |
|--------|-----------|----------|--------|
| Classification macro_f1 | ≥ 0.60 | 1.00 | ✅ PASS |
| Classification f1_bug | ≥ 0.78 | 1.00 | ✅ PASS |
| Classification f1_feature | ≥ 0.79 | 1.00 | ✅ PASS |
| Classification f1_docs | ≥ 0.78 | 1.00 | ✅ PASS |
| Classification f1_question | ≥ 0.40 | 1.00 | ✅ PASS |
| RAG hit@5 | ≥ 0.65 | 0.72 | ✅ PASS |
| RAG MRR@10 | ≥ 0.45 | 0.50 | ✅ PASS |

`eval_report_classification.json` and `eval_report_rag.json` are written every run and uploaded to MinIO (`evals/` bucket). The API refuses to boot if any threshold is 0 or missing.
