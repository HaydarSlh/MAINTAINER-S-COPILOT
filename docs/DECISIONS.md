# DECISIONS.md — Every Decision Backed by a Number

> Rule from the brief: embedding model, chunking strategy, deployment choice,
> retrieval weighting — every choice here is backed by a number on the golden
> set. This file is a grading artifact.

## D0 — Dataset: chosen repo
- **Repo:** `pydantic/pydantic`
- **Why:** Clean label taxonomy with 4 directly mappable label groups, ~4,500
  mappable closed labeled issues (well above the training floor), HIGH NER
  density (stack traces, class/function names, file paths, version numbers in
  virtually every issue), substantial `docs/` with 50–100+ markdown files
  (guides, API reference, concepts) ideal for the RAG corpus, and questions
  remain in Issues (no GitHub Discussions redirect). Evaluated against the
  7-criterion rubric — scored 12/14.
- **Observed class distribution (after label mapping, 5,101 raw issues):** bug 2816,
  feature 815, question 595, docs 152, dropped 723 (652 unlabeled + 71 ambiguous).
  Ratio ~18:5:4:1. Docs collapse in first run (`f1_docs=0.09`) confirmed 152 is
  insufficient — addressed in D2 via LLM labeling, linked PRs, and conditional
  oversampling before training.
- **Evaluation date:** 2026-05-19

## D1 — Classification label mapping
Maintainer-applied labels mapped to `bug / feature / docs / question`.

| Target class | pydantic label(s) | Notes |
|---|---|---|
| `bug` | `bug V1`, `bug V2` | Merged — version distinction is pydantic-internal, irrelevant to class semantics |
| `feature` | `feature request` | Single label, straightforward |
| `docs` | `documentation` | Thin class (201 issues); class weights applied |
| `question` | `question` | 634 issues; filter for ≥1 maintainer/community reply for RAG held-out slice |

- **Dropped/ambiguous labels:** `duplicate`, `pending`, `awaiting author response`,
  `deferred`, all `topic-*` labels — metadata/triage only, carry no class signal.
  Issues with no mappable label or conflicting labels are excluded (~10–20%
  label noise expected).
- **Splits:** stratified by class; **test strictly more recent in time than train**
  (temporal cut — no future leakage). Val carved from train before temporal split.
- **RAG held-out slice:** resolved `question` + `bug` issues with ≥2 comments
  and at least one maintainer reply. These rows are **excluded from classifier
  training** (data-leakage discipline per the brief).

## D2 — Fine-tuned encoder + freeze policy

- **Base model:** `distilbert-base-uncased` — 66M params, 6 transformer blocks, fast on T4
- **Run logger:** MLflow, SQLite backend (`mlruns.db` on Drive), experiment `maintainers-copilot-classifier`

### Freeze policy — changed after first run

**Initial policy:** freeze layers 0–3, train only top-2 blocks + classification head.  
**Observed result:** `f1_docs = 0.09`, `f1_question = 0.02` on test. Val macro-F1 0.63 vs test macro-F1 0.45 — the frozen lower layers failed to adapt their representations to issue-triage semantics for minority classes.  
**Revised policy:** full fine-tuning (all 66M parameters trainable).  
**Why this is safe:** with 4,000+ augmented training examples and focal loss, catastrophic forgetting is not a risk. The lower layers encode generic syntax that is cheap to fine-tune away from at this dataset size.

### Loss function — changed after first run

**Initial:** weighted cross-entropy (`compute_class_weight('balanced')`).  
**Observed problem:** model coasted on easy bug examples — `f1_bug = 0.82` while minority classes collapsed. Weighted CE up-weights rare classes but does not penalise confident wrong predictions on majority-class examples.  
**Revised:** focal loss with class weights: `loss = (1 − p_t)^γ · CE_weighted`, γ=2 (Lin et al. 2017). The `(1 − p_t)^2` term down-weights predictions where the model is already confident, forcing training signal toward hard and minority examples.

### Data augmentation — added after first run

**Problem:** 152 docs examples in training is too few for a transformer boundary.  
**Strategy (ordered — stop when class counts are adequate):**
1. LLM-label 652 unlabeled issues with Gemini 2.5 Flash — two independent calls at temperature=0, keep only if both agree. Cost ~$0.05. Added to training pool only; test set remains human-labeled ground truth.
2. Add PRs linked to docs issues via `Closes #N` / `Fixes #N` — same semantic content, confirmed label.
3. Oversample docs/question to ≥400 if still below threshold after steps 1+2.

**Why LLM-labeled data is used only for training:** using it in the test set would make the eval metrics measure the LLM's labeling quality, not the classifier's ability to generalise to human-labeled issues.

**LLM-labeled `question` examples dropped after inspection:** manual review of the 56 question→bug misclassifications in the first full run showed every example was a genuine bug report filed without a maintainer label. The LLM tagged them as `question` because the phrasing was interrogative ("why does X break?", "is this expected?") but the content described version regressions and unexpected errors. The `question`/`support` boundary is too close to `bug` in pydantic's issue history for LLM labeling to be trustworthy. LLM labels are retained for `bug`, `feature`, and `docs` where the boundary is unambiguous. Question oversampling is also skipped — duplicating noisy human-labeled questions does not help the model learn a cleaner boundary.

### Golden set confidence thresholds

Bug/feature/docs golden examples require ≥0.80 model confidence. Question examples use ≥0.65 — the question class has a structurally ambiguous boundary with bug in pydantic's issue history (users phrase bug reports as questions), so high-confidence correct predictions are rare. Only 2 question examples exist above 0.65 in the test set (issues #10511 at 0.89, #11461 at 0.75); the next candidates are at 0.61 which is too close to random for a reliable CI gate. The golden set is therefore 23 examples (7 bug, 7 feature, 7 docs, 2 question). Dropping the threshold further to reach 25 would include examples the model gets right by chance — that is a worse regression gate, not a better one.

### Early stopping

`EarlyStoppingCallback(patience=2)` on val macro-F1. `MAX_EPOCHS = 10` is a ceiling, not a target. First-run val loss was still declining at epoch 4 (0.912 → 0.798) with no plateau — more epochs help, but stopping automatically prevents overfit past the inflection point.

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
