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

### Low-confidence fallback (classifier)
When the fine-tuned model's top-class probability falls below a per-class threshold,
classification falls back to the LLM baseline (Gemini 2.5 Flash, same prompt as Section 9
of the training notebook). This is particularly important for the `question` class where
test F1 = 0.087 and the model boundary with `bug` is structurally ambiguous.

**Fallback thresholds (same as golden-set confidence floors):**

| Class | DL confidence threshold | Rationale |
|-------|------------------------|-----------|
| bug | 0.60 | High-confidence class; only fall back on genuine uncertainty |
| feature | 0.60 | High-confidence class |
| docs | 0.60 | High-confidence class |
| question | 0.50 | Lower threshold — model is unreliable here; cast wider net to LLM |

**Result field:** `Classification.fallback_used: bool` so callers know which path fired.
**Why not always use LLM:** latency (~1–2s vs ~10ms), API cost, and the DL model is
correct >87% of the time on bug/feature/docs. The fallback fires only on the tail.

## D4 — Embedding model
- **Candidates:** `sentence-transformers/all-MiniLM-L6-v2` (384-dim, general purpose)
  vs `sentence-transformers/multi-qa-mpnet-base-dot-v1` (768-dim, trained for Q→passage retrieval)
- **Metric:** hit@5 and MRR@10 on RAG golden set (25 triples), using structure-aware chunks
  and pure dense retrieval (hybrid added in D6 to isolate the embedding effect)
- **Result:** _TBD after rag/experiments.py Section 5_
- **Choice:** _TBD — expected: multi-qa-mpnet wins because it is trained for the exact
  question-to-passage task; MiniLM is a fallback if latency is a constraint_

## D5 — Chunking strategy (not naive fixed-size)

### Corpus structure
Two document types with different natural granularity:
- **Pydantic docs** (~60 markdown files): structured with `##`/`###` headers, code blocks,
  Material for MkDocs admonitions (`!!!`, `???`). Each `##` section is a complete semantic
  unit (e.g. "Field validators", "Model validators", "Raising validation errors").
- **Resolved Q&A issues** (~300 held-out issues): title + body + top maintainer reply.
  Already a natural semantic unit — no further splitting needed.

### What we compared

| Strategy | Description |
|----------|-------------|
| **Baseline** | Fixed-size 512 tokens, 50-token overlap — splits mid-sentence, breaks code examples |
| **Candidate** | Structure-aware: split docs on `##` headers (keep header as chunk prefix); whole-issue for Q&A |

- **Why structure-aware beats fixed-size here:** pydantic docs have high code-example density.
  A fixed cut mid-example gives a chunk with dangling code that has no semantic meaning alone.
  Structure-aware chunks keep explanation + code example + API reference together.
- **Naive baseline number (hit@5):** _TBD_
- **Structure-aware number (hit@5):** _TBD_

### Techniques considered and rejected

| Technique | Why rejected |
|-----------|-------------|
| Parent-document retrieval | Structure-aware chunks are already full sections (200–600 tokens). Parent-doc helps when chunks are tiny (50–100 tokens). Not needed here. |
| Sliding window with overlap | Overlap helps fixed-size chunking but adds duplicate content to the index. Structure-aware has no boundary problem to solve. |
| Semantic chunking (embedding-based splits) | More expensive, no clear gain when document structure already defines good boundaries. |

## D6 — Hybrid retrieval weighting

### What we compared

| Strategy | Description |
|----------|-------------|
| **Baseline** | Pure dense (bi-encoder vector search only) |
| **Candidate** | Hybrid: BM25 sparse + dense, combined as `α × dense + (1−α) × BM25` |

- **Why hybrid matters for this corpus:** pydantic issues have very high identifier density —
  exact class names (`BaseModel`, `model_validate`), error types (`ValidationError`),
  decorator names (`@field_validator`). BM25 exact-matches these perfectly; dense vectors
  sometimes miss exact tokens. Hybrid captures both.
- **Alpha tuning:** tested α ∈ {0.3, 0.5, 0.7} on the golden set; picked the best.
- **Best alpha:** _TBD_
- **Pure dense hit@5:** _TBD_ | **Hybrid hit@5:** _TBD_

### Techniques considered and rejected

| Technique | Why rejected |
|-----------|-------------|
| Pure BM25 only | Misses semantic paraphrases — "validate data" vs "use validators". Dense is needed. |
| Learned sparse (SPLADE) | Requires a separate model, more complex infra. BM25 is sufficient at this corpus size. |

## D7 — Reranking & query transformation

### D7a — Cross-encoder reranking

| Setup | Description |
|-------|-------------|
| **Baseline** | Hybrid k=5, take top-5 as-is |
| **Candidate** | Hybrid k=20, rerank with `cross-encoder/ms-marco-MiniLM-L-6-v2`, take top-5 |

- **Why cross-encoder over bi-encoder for reranking:** bi-encoder embeds query and passage
  independently; cross-encoder sees both together and scores relevance jointly — much more
  accurate but too slow for first-stage retrieval over thousands of chunks.
- **Why ms-marco-MiniLM-L-6-v2:** local (no API), runs fast on CPU (20 candidates ~50ms),
  trained on MS-MARCO passage relevance which transfers well to Q&A over technical docs.
- **Baseline hit@5:** _TBD_ | **With reranking hit@5:** _TBD_

### Techniques considered and rejected for reranking

| Technique | Why rejected |
|-----------|-------------|
| Cohere reranker API | External API dependency, per-call cost, latency add. Local model is sufficient. |
| ColBERT | Requires a dedicated ColBERT server (dedicated GPU or large RAM). Overkill for this corpus size. |

### D7b — Query transformation

Tested one at a time on top of the best pipeline from D7a:

| Technique | How it works | When it helps |
|-----------|-------------|---------------|
| **None (baseline)** | Raw question sent directly to retrieval | — |
| **Multi-query** | LLM generates 3 paraphrases; retrieve for each; deduplicate | Vocab mismatch between how maintainers phrase questions and how docs are written |
| **HyDE** | LLM generates a hypothetical answer; embed that instead of the question | Question and answer are phrased very differently (question is problem-shaped, docs are solution-shaped) |
| **Step-back** | LLM abstracts the question first ("why does X fail?" → "how does pydantic validation work?") then retrieves | Conceptual "why" questions that need background context |

- **Multi-query hit@5:** _TBD_
- **HyDE hit@5:** _TBD_
- **Step-back hit@5:** _TBD_
- **Chosen technique:** _TBD — pick highest; stack multi-query + step-back if complementary_

### Techniques considered and rejected for query transformation

| Technique | Why rejected |
|-----------|-------------|
| Decomposition | Most maintainer questions are single-hop. Measured first — only add if hit@5 still below threshold after D7b. |
| Agentic RAG (retrieval as tool) | Pipeline shape is fixed by the brief. Full agentic routing adds latency and complexity beyond project scope. |
| GraphRAG | Pydantic docs do not have a deep entity relationship graph (it is a library reference, not a knowledge base). Community summary approach also unnecessary at this corpus size. |
| Routing | Only one corpus type (docs + issues); no routing decision to make. |

## D8 — Long-term memory type
- **Choice (episodic | semantic | procedural):** _TBD + defense_

## D9 — Tracing backend
- **Choice:** _TBD — because (one line)_

## D10 — Vector store
- **pgvector vs Qdrant:** _TBD + defense_

## D11 — RAG eval methodology
- **Method:** RAGAS with Gemini 2.5 Flash as the frozen judge for faithfulness and
  answer_relevancy. Human labels on 5 of 25 golden examples to report judge agreement.
- **Why RAGAS over a custom judge:** RAGAS provides reproducible, decomposed metrics
  (faithfulness separates "did the answer hallucinate" from "was the answer relevant").
  A custom prompt judge collapses these into one score, making debugging harder.
- **Human/judge agreement:** _TBD after hand-labeling 5 examples_
- **Faithfulness:** _TBD_ | **Answer relevancy:** _TBD_

## D12 — LLM provider + model
- **Primary:** Gemini 2.5 Flash (`gemini-2.5-flash`) via `google-genai` SDK.
  API key stored in Vault at `secret/llm.api_key`.
- **Backup:** Anthropic Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) via `anthropic` SDK.
  API key stored in Vault at `secret/llm.anthropic_api_key`.
- **Fallback logic:** if Gemini returns 503/429 after backoff exhaustion, the LLM adapter
  automatically retries the same call on Claude Haiku. The caller sees a transparent result
  with `provider` field indicating which model answered.
- **Why Gemini as primary:** already integrated in training notebook, low cost, fast (~1s
  for classification prompts). Haiku is the backup because it is comparably fast and cheap,
  and Anthropic and Google outages are unlikely to overlap.
- **Why not GPT-4o as backup:** adds a third API key to manage in Vault with no quality
  advantage for this use case.

## D13 — Short-term memory TTL
- **TTL value:** 1800 seconds (30 minutes)
- **Justification:** Long enough to cover a focused issue-triage session without
  leaving stale context if the maintainer closes the tab and returns the next day.
  A typical triage session (read issue, classify, search docs, write response) takes
  5–15 minutes. 30 minutes gives comfortable headroom without persisting context
  into the next working day.
- **Boundary behavior:** on TTL expiry the Redis key is deleted. The next message
  from the user starts a fresh context window. The chat service checks for a None
  return from `get_short_term()` and informs the user their session expired —
  it does NOT silently continue with a missing context (that would produce
  confused responses). Long-term memory (pgvector) is unaffected by the TTL.
