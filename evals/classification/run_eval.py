"""Run the classification golden set against ALL THREE models.

Computes macro-F1, per-class F1, and the confusion matrix for classical /
fine-tuned / LLM. The deployed model's numbers are gated by
eval_thresholds.yaml; all three are reported. Feeds evals/report.py.

Exit codes:
  0  — all thresholds passed (or --no-gate flag set)
  1  — one or more thresholds breached
  2  — fatal error (missing artifacts, Vault unreachable, etc.)

Usage:
  python -m evals.classification.run_eval [--model-dir PATH] [--no-gate]
                                          [--no-llm] [--no-classical]
                                          [--out PATH]
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import yaml
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
)

# ── Repo root on sys.path so intra-project imports work ──────────────────────
_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

GOLDEN_SET = Path(__file__).with_name("golden_set.jsonl")
THRESHOLDS_FILE = _REPO / "eval_thresholds.yaml"
LABELS = ["bug", "feature", "docs", "question"]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}
ID2LABEL = {i: l for l, i in LABEL2ID.items()}


# ─────────────────────────── helpers ─────────────────────────────────────────

def _load_golden() -> list[dict]:
    examples = []
    with open(GOLDEN_SET) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    if not examples:
        print("FATAL: golden_set.jsonl is empty", file=sys.stderr)
        sys.exit(2)
    return examples


def _load_thresholds() -> dict:
    with open(THRESHOLDS_FILE) as f:
        return yaml.safe_load(f)


def _metrics(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    """Return macro-F1, per-class F1, and confusion matrix."""
    per_class = f1_score(y_true, y_pred, labels=LABELS, average=None, zero_division=0)
    macro = f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=LABELS).tolist()
    return {
        "macro_f1": round(float(macro), 4),
        "per_class_f1": {l: round(float(per_class[i]), 4) for i, l in enumerate(LABELS)},
        "confusion_matrix": {"labels": LABELS, "matrix": cm},
        "n": len(y_true),
    }


def _gate(metrics: dict[str, Any], thresholds: dict, model_name: str) -> list[str]:
    """Return list of failure messages; empty → passed."""
    failures: list[str] = []
    cfg = thresholds.get("classification", {})

    macro = metrics["macro_f1"]
    floor = cfg.get("macro_f1_min", 0)
    if macro < floor:
        failures.append(
            f"[{model_name}] macro_f1 {macro:.4f} < threshold {floor}"
        )

    per_floor = cfg.get("per_class_f1_min", {})
    for label, f1 in metrics["per_class_f1"].items():
        label_floor = per_floor.get(label, 0)
        if f1 < label_floor:
            failures.append(
                f"[{model_name}] f1_{label} {f1:.4f} < threshold {label_floor}"
            )

    return failures


# ─────────────────────────── fine-tuned model ────────────────────────────────

def _run_finetuned(examples: list[dict], model_dir: str) -> list[str]:
    """Classify all examples with the deployed DistilBERT model."""
    from modelserver.pipelines.classifier import classify

    preds = []
    for ex in examples:
        result = classify(ex["text"], model_dir)
        preds.append(result.label)
    return preds


# ─────────────────────────── classical model ─────────────────────────────────

def _fetch_classical_model() -> Any:
    """Download classical model from MinIO and return fitted pipeline."""
    try:
        import joblib
        from minio import Minio
    except ImportError as e:
        print(f"WARNING: cannot import minio/joblib ({e}); skipping classical", file=sys.stderr)
        return None

    endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
    bucket = "models"
    obj_key = "classifier/classical_pipeline.joblib"

    try:
        client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
        data = client.get_object(bucket, obj_key)
        buf = io.BytesIO(data.read())
        return joblib.load(buf)
    except Exception as e:
        print(f"WARNING: classical model not available ({e}); skipping", file=sys.stderr)
        return None


def _run_classical(examples: list[dict], pipeline: Any) -> list[str]:
    texts = [ex["text"] for ex in examples]
    raw = pipeline.predict(texts)
    return [str(p) for p in raw]


# ─────────────────────────── LLM baseline ────────────────────────────────────

def _run_llm(examples: list[dict]) -> list[str | None]:
    """Classify all examples with the Gemini LLM baseline.

    Returns None for any example where the model returns an invalid or empty
    label (treated as abstain; counted as incorrect in metrics).
    """
    try:
        import google.genai as genai
    except ImportError:
        print("WARNING: google-genai not installed; skipping LLM baseline", file=sys.stderr)
        return [None] * len(examples)

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        # Try Vault if available
        try:
            from app.infra.vault import read_secret
            api_key = read_secret("secret/data/llm").get("api_key", "")
        except Exception:
            pass

    if not api_key:
        print("WARNING: GOOGLE_API_KEY not set and Vault unavailable; skipping LLM baseline", file=sys.stderr)
        return [None] * len(examples)

    client = genai.Client(api_key=api_key)

    _PROMPT = (
        "Classify the following GitHub issue into exactly one of: "
        "bug, feature, docs, question.\n"
        "Reply with only the single word label, nothing else.\n\n"
        "Issue:\n{text}\n\nLabel:"
    )

    preds: list[str | None] = []
    for ex in examples:
        label = _llm_classify_one(client, _PROMPT, ex["text"])
        preds.append(label)
    return preds


def _llm_classify_one(client: Any, prompt_tmpl: str, text: str, max_retries: int = 6) -> str | None:
    delay = 5
    for attempt in range(max_retries):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_tmpl.format(text=text[:2000]),
            )
            raw = (resp.text or "").strip().lower()
            return raw if raw in LABEL2ID else None
        except Exception as e:
            msg = str(e)
            if attempt < max_retries - 1 and ("503" in msg or "429" in msg or "UNAVAILABLE" in msg):
                print(f"  LLM transient error ({msg[:60]}), retry in {delay}s ...", file=sys.stderr)
                time.sleep(delay)
                delay = min(delay * 2, 120)
            else:
                print(f"  LLM error: {msg[:120]}", file=sys.stderr)
                return None
    return None


# ─────────────────────────── report writer ───────────────────────────────────

def _write_report(report: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report written → {out_path}")


def _upload_report(report: dict, out_path: Path) -> None:
    """Best-effort upload to MinIO; never blocks the gate."""
    try:
        import json as _json
        from minio import Minio

        endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
        bucket = "evals"

        client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

        data = _json.dumps(report, indent=2).encode()
        client.put_object(bucket, "classification/eval_report.json", io.BytesIO(data), len(data))
        print(f"Report uploaded → minio://{bucket}/classification/eval_report.json")
    except Exception as e:
        print(f"WARNING: MinIO upload failed ({e}); report is local-only", file=sys.stderr)


# ─────────────────────────── main ────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Classification golden-set eval")
    parser.add_argument("--model-dir", default=os.environ.get("CLASSIFIER_MODEL_DIR", ""),
                        help="Path to fetched DistilBERT model directory")
    parser.add_argument("--no-gate", action="store_true",
                        help="Compute metrics but skip threshold gate (exit 0)")
    parser.add_argument("--no-llm", action="store_true",
                        help="Skip LLM baseline (saves ~30s and API quota)")
    parser.add_argument("--no-classical", action="store_true",
                        help="Skip classical ML baseline")
    parser.add_argument("--out", default=str(_REPO / "eval_report.json"),
                        help="Path to write eval_report.json")
    args = parser.parse_args()

    examples = _load_golden()
    thresholds = _load_thresholds()
    y_true = [ex["label"] for ex in examples]

    print(f"Golden set: {len(examples)} examples — {dict(zip(*[[l for l in LABELS], [y_true.count(l) for l in LABELS]]))}")

    report: dict[str, Any] = {
        "golden_set_size": len(examples),
        "models": {},
        "gate_failures": [],
        "passed": True,
    }

    # ── Fine-tuned model (the deployed model — gated) ─────────────────────────
    if not args.model_dir:
        print("FATAL: --model-dir is required (or set CLASSIFIER_MODEL_DIR env var)", file=sys.stderr)
        sys.exit(2)

    print(f"\n── Fine-tuned DistilBERT ({args.model_dir}) ──")
    try:
        ft_preds = _run_finetuned(examples, args.model_dir)
        ft_metrics = _metrics(y_true, ft_preds)
        report["models"]["finetuned"] = ft_metrics
        print(classification_report(y_true, ft_preds, labels=LABELS, zero_division=0))

        if not args.no_gate:
            failures = _gate(ft_metrics, thresholds, "finetuned")
            if failures:
                report["gate_failures"].extend(failures)
                report["passed"] = False
                for msg in failures:
                    print(f"  FAIL  {msg}")
            else:
                print(f"  PASS  macro_f1={ft_metrics['macro_f1']:.4f} — all thresholds met")
    except Exception as e:
        print(f"ERROR running fine-tuned model: {e}", file=sys.stderr)
        report["models"]["finetuned"] = {"error": str(e)}
        if not args.no_gate:
            report["gate_failures"].append(f"[finetuned] model error: {e}")
            report["passed"] = False

    # ── Classical model (reference — not gated) ───────────────────────────────
    if not args.no_classical:
        print("\n── Classical ML baseline ──")
        pipeline = _fetch_classical_model()
        if pipeline is not None:
            try:
                cl_preds = _run_classical(examples, pipeline)
                cl_metrics = _metrics(y_true, cl_preds)
                report["models"]["classical"] = cl_metrics
                print(classification_report(y_true, cl_preds, labels=LABELS, zero_division=0))
            except Exception as e:
                print(f"ERROR running classical model: {e}", file=sys.stderr)
                report["models"]["classical"] = {"error": str(e)}
        else:
            report["models"]["classical"] = {"skipped": "artifact unavailable"}

    # ── LLM baseline (reference — not gated) ─────────────────────────────────
    if not args.no_llm:
        print("\n── LLM baseline (Gemini 2.5 Flash) ──")
        llm_preds_raw = _run_llm(examples)
        # Replace None abstentions with a sentinel that scores as wrong
        llm_preds = [p if p is not None else "__abstain__" for p in llm_preds_raw]
        abstentions = llm_preds_raw.count(None)
        if abstentions:
            print(f"  {abstentions}/{len(examples)} abstentions (invalid/empty response)")
        try:
            llm_metrics = _metrics(y_true, llm_preds)
            llm_metrics["abstentions"] = abstentions
            report["models"]["llm"] = llm_metrics
            print(classification_report(y_true, llm_preds, labels=LABELS, zero_division=0))
        except Exception as e:
            print(f"ERROR computing LLM metrics: {e}", file=sys.stderr)
            report["models"]["llm"] = {"error": str(e)}

    # ── Write + upload report ─────────────────────────────────────────────────
    _write_report(report, Path(args.out))
    _upload_report(report, Path(args.out))

    # ── Exit code ─────────────────────────────────────────────────────────────
    if not args.no_gate and not report["passed"]:
        print("\nCI GATE FAILED:")
        for msg in report["gate_failures"]:
            print(f"  {msg}")
        sys.exit(1)

    print("\nAll gates passed." if not args.no_gate else "\n--no-gate: skipping exit-code gate.")


if __name__ == "__main__":
    main()
