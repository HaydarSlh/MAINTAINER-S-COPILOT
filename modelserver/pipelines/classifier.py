"""Fine-tuned DistilBERT classifier — load, SHA-check, predict.

Loaded ONCE at modelserver startup. The refuse-to-boot guard in
modelserver/main.py calls verify_weights() before serving any requests.
The model card (app/artifacts/model_card.json) is the source of truth for
the expected SHA-256; a mismatch means stale or tampered weights.
"""

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# ── Label schema (must match notebooks/training.ipynb LABEL_MAP) ──────────────
ID2LABEL = {0: "bug", 1: "feature", 2: "docs", 3: "question"}
LABEL2ID = {v: k for k, v in ID2LABEL.items()}
MAX_LENGTH = 256


@dataclass
class ClassificationResult:
    label: str          # one of bug / feature / docs / question
    label_id: int
    confidence: float   # softmax probability of the top class
    all_scores: dict[str, float]   # {label: probability} for all 4 classes


def _load_model_card(card_path: Path) -> dict:
    with open(card_path) as f:
        return json.load(f)


def verify_weights(weights_path: Path, card_path: Path) -> None:
    """Assert weights SHA-256 matches the committed model card.

    Called by modelserver/main.py before the app starts serving. Raises
    RuntimeError on mismatch so the container exits and compose restarts it
    rather than serving stale predictions silently.
    """
    card = _load_model_card(card_path)
    expected_sha = card.get("weights_sha256", "")
    if expected_sha in ("TBD", "", None):
        raise RuntimeError(
            "model_card.json has no committed weights_sha256. "
            "Run the training notebook (Section 11) and commit the card."
        )

    with open(weights_path, "rb") as f:
        actual_sha = hashlib.sha256(f.read()).hexdigest()

    if actual_sha != expected_sha:
        raise RuntimeError(
            f"Classifier weights SHA-256 mismatch.\n"
            f"  Expected (model card): {expected_sha}\n"
            f"  Actual  (file):        {actual_sha}\n"
            "Upload the correct weights to MinIO and re-fetch, or retrain."
        )


@lru_cache(maxsize=1)
def _get_model_and_tokenizer(model_dir: str):
    """Load tokenizer + model once; cache for the process lifetime."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_dir,
        num_labels=len(ID2LABEL),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )
    model.to(device)
    model.eval()
    return tokenizer, model, device


def classify(text: str, model_dir: str) -> ClassificationResult:
    """Classify a single issue text into bug / feature / docs / question.

    Args:
        text:      Raw issue text (title + body concatenated, as prepared by
                   the training notebook's clean_text function).
        model_dir: Path to the fetched model directory (weights + tokenizer).

    Returns:
        ClassificationResult with the predicted label and confidence scores.
    """
    tokenizer, model, device = _get_model_and_tokenizer(model_dir)

    inputs = tokenizer(
        text,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    ).to(device)

    # DistilBERT has no token_type_ids; drop them if tokenizer adds them.
    inputs = {k: v for k, v in inputs.items() if k != "token_type_ids"}

    with torch.no_grad():
        logits = model(**inputs).logits

    probs = torch.softmax(logits, dim=-1).squeeze().cpu().tolist()
    label_id = int(torch.argmax(logits, dim=-1).item())

    return ClassificationResult(
        label=ID2LABEL[label_id],
        label_id=label_id,
        confidence=probs[label_id],
        all_scores={ID2LABEL[i]: round(p, 4) for i, p in enumerate(probs)},
    )
