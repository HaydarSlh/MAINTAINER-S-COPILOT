"""Shared eval-report writer + regression gate.

Writes eval_report.json every run, uploads it to MinIO, fetches the previous
green build's report, and fails if any metric drops below the committed
threshold or beyond regression_tolerance (eval_thresholds.yaml).
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any


def write_report(results: dict[str, Any], out_path: Path) -> None:
    """Serialize results to JSON at out_path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)


def fetch_previous_report(bucket: str = "evals", key: str = "classification/eval_report.json") -> dict | None:
    """Pull the last-uploaded eval_report.json from MinIO. Returns None if unavailable."""
    try:
        from minio import Minio

        endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
        client = Minio(
            endpoint,
            access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
            secure=False,
        )
        data = client.get_object(bucket, key)
        return json.loads(data.read().decode())
    except Exception:
        return None


def upload_report(results: dict[str, Any], bucket: str = "evals",
                  key: str = "classification/eval_report.json") -> None:
    """Best-effort upload to MinIO; does not raise on failure."""
    try:
        from minio import Minio

        endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
        client = Minio(
            endpoint,
            access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
            secure=False,
        )
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        raw = json.dumps(results, indent=2).encode()
        client.put_object(bucket, key, io.BytesIO(raw), len(raw))
    except Exception:
        pass


def gate(
    results: dict[str, Any],
    thresholds: dict[str, Any],
    previous: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """Check results against absolute floors and regression tolerance.

    Args:
        results:    The current eval_report (output of run_eval.py).
        thresholds: Parsed eval_thresholds.yaml.
        previous:   Previous green-build report; None skips regression check.

    Returns:
        (passed, failures) where failures is a list of human-readable messages.
    """
    failures: list[str] = []
    cfg = thresholds.get("classification", {})
    tolerance = float(thresholds.get("regression_tolerance", 0.03))
    model_metrics: dict = results.get("models", {}).get("finetuned", {})

    if "error" in model_metrics:
        return False, [f"finetuned model error: {model_metrics['error']}"]

    macro = model_metrics.get("macro_f1", 0.0)
    per_class = model_metrics.get("per_class_f1", {})

    # ── Absolute floors ───────────────────────────────────────────────────────
    macro_floor = cfg.get("macro_f1_min", 0)
    if macro < macro_floor:
        failures.append(f"macro_f1 {macro:.4f} < floor {macro_floor}")

    for label, floor in cfg.get("per_class_f1_min", {}).items():
        f1 = per_class.get(label, 0.0)
        if f1 < floor:
            failures.append(f"f1_{label} {f1:.4f} < floor {floor}")

    # ── Regression tolerance ──────────────────────────────────────────────────
    if previous:
        prev_metrics = previous.get("models", {}).get("finetuned", {})
        prev_macro = prev_metrics.get("macro_f1", 0.0)
        if macro < prev_macro - tolerance:
            failures.append(
                f"macro_f1 regression: {macro:.4f} vs previous {prev_macro:.4f} "
                f"(tolerance {tolerance})"
            )

        prev_per_class = prev_metrics.get("per_class_f1", {})
        for label in LABELS:
            f1 = per_class.get(label, 0.0)
            prev_f1 = prev_per_class.get(label, 0.0)
            if f1 < prev_f1 - tolerance:
                failures.append(
                    f"f1_{label} regression: {f1:.4f} vs previous {prev_f1:.4f} "
                    f"(tolerance {tolerance})"
                )

    return len(failures) == 0, failures


LABELS = ["bug", "feature", "docs", "question"]
