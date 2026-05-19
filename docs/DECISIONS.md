# DECISIONS.md — Every Decision Backed by a Number

> Rule from the brief: embedding model, chunking strategy, deployment choice,
> retrieval weighting — every choice here is backed by a number on the golden
> set. This file is a grading artifact.

## D0 — Dataset: chosen repo
- **Repo:** _TBD (locked Monday morning, lived with all week)_
- **Why:** _TBD_

## D1 — Classification label mapping
Maintainer-applied labels mapped to `bug / feature / docs / question`.
- **Mapping table:** _TBD_
- **Dropped/ambiguous labels & why:** _TBD_
- **Splits:** stratified; test strictly more recent in time than train.

## D2 — Fine-tuned encoder + freeze policy
- **Base model:** _TBD (small encoder)_
- **Freeze policy:** _TBD + defense_
- **Run logger:** _TBD_

## D3 — Three-way classifier comparison (the deployment choice)
| Model | Accuracy | Macro-F1 | Per-class F1 | Latency | Cost |
|-------|---------|----------|--------------|---------|------|
| Classical ML | _ | _ | _ | _ | _ |
| Fine-tuned encoder | _ | _ | _ | _ | _ |
| LLM baseline | _ | _ | _ | _ | _ |
- **Deployment choice:** _TBD — because (one line)_

## D4 — Embedding model
- **Chosen:** _TBD_ vs alternative _TBD_
- **Retrieval-quality number on golden set:** _TBD_

## D5 — Chunking strategy (not naive fixed-size)
- **Strategy:** _TBD_, with golden-set number vs the naive baseline.

## D6 — Hybrid retrieval weighting
- **Sparse+dense weighting:** _TBD (tuned value + number)_

## D7 — Reranking & query transformation
- **Cross-encoder:** _TBD_
- **Query transformation technique:** _TBD_

## D8 — Long-term memory type
- **Choice (episodic | semantic | procedural):** _TBD + defense_

## D9 — Tracing backend
- **Choice:** _TBD — because (one line)_

## D10 — Vector store
- **pgvector vs Qdrant:** _TBD + defense_

## D11 — RAG eval methodology
- **RAGAS vs frozen judge:** _TBD_; human/judge agreement on 5 hand-labeled.

## D12 — LLM provider + model
- **Choice:** _TBD_

## D13 — Short-term memory TTL
- **TTL value + justification + boundary behavior:** _TBD_
