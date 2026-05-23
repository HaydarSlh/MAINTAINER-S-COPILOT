"""Issue classification business logic.

Calls the deployed fine-tuned classifier via modelserver HTTP client.
If the model's confidence is below the per-class threshold, falls back
to the LLM baseline (Gemini → Claude Haiku) for a second opinion.
Fallback thresholds and rationale recorded in DECISIONS.md D3.
"""

from __future__ import annotations

from pathlib import Path

from app.domain.enums import IssueLabel
from app.domain.models import Classification
from app.infra import modelserver_client

# ── Per-class confidence thresholds for LLM fallback ─────────────────────────
# Below these values the DL model is too uncertain; LLM gives a better answer.
# question threshold is lower because the DL boundary with bug is structurally
# ambiguous (test F1 = 0.087) — cast a wider net to the LLM for this class.
_FALLBACK_THRESHOLD: dict[str, float] = {
    "bug":      0.60,
    "feature":  0.60,
    "docs":     0.60,
    "question": 0.50,
}

_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "llm_classifier_baseline.md"
_PROMPT_TEMPLATE: str | None = None

_VALID_LABELS = {"bug", "feature", "docs", "question"}


def _prompt_template() -> str:
    """Load and cache the LLM classifier baseline prompt from disk."""
    global _PROMPT_TEMPLATE
    if _PROMPT_TEMPLATE is None:
        _PROMPT_TEMPLATE = _PROMPT_PATH.read_text(encoding="utf-8")
    return _PROMPT_TEMPLATE


def _llm_classify(text: str) -> str | None:
    """Call the LLM baseline. Returns label string or None on failure."""
    from app.infra.llm import chat

    prompt = _prompt_template().replace("{text}", text[:3000])
    try:
        resp = chat([{"role": "user", "content": prompt}])
        label = (resp.content or "").strip().lower()
        return label if label in _VALID_LABELS else None
    except Exception:
        return None


async def classify_issue(text: str) -> Classification:
    """Classify a GitHub issue text into bug / feature / docs / question.

    Pipeline:
      1. Call fine-tuned DistilBERT via modelserver HTTP endpoint.
      2. If confidence < per-class threshold → call LLM fallback.
      3. If LLM also fails → return DL result as-is (degrade gracefully).

    Returns:
        Classification with label, confidence, and fallback_used flag.
    """
    # Step 1 — fine-tuned model
    try:
        dl_result = await modelserver_client.classify(text)
    except Exception as e:
        # Modelserver down — go straight to LLM, mark as fallback
        llm_label = _llm_classify(text)
        if llm_label:
            return Classification(
                label=IssueLabel(llm_label),
                confidence=0.0,
                fallback_used=True,
            )
        raise RuntimeError(f"Both modelserver and LLM classifier unavailable: {e}") from e

    label: str = dl_result["label"]
    confidence: float = dl_result["confidence"]

    # Step 2 — low-confidence fallback
    threshold = _FALLBACK_THRESHOLD.get(label, 0.60)
    if confidence < threshold:
        llm_label = _llm_classify(text)
        if llm_label:
            return Classification(
                label=IssueLabel(llm_label),
                confidence=confidence,   # keep original DL confidence for transparency
                fallback_used=True,
            )
        # LLM also failed — fall through to DL result

    # Step 3 — return DL result (high confidence, or fallback failed)
    return Classification(
        label=IssueLabel(label),
        confidence=confidence,
        fallback_used=False,
    )
