"""Shared eval-report writer + regression gate.

Writes eval_report.json every run, uploads it to MinIO, fetches the previous
green build's report, and fails if any metric drops below the committed
threshold or beyond regression_tolerance (eval_thresholds.yaml).
"""

# TODO: write_report(results), gate(results, thresholds, previous) -> pass/fail
