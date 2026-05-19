"""Run the classification golden set against ALL THREE models.

Computes macro-F1, per-class F1, and the confusion matrix for classical /
fine-tuned / LLM. The deployed model's numbers are gated by
eval_thresholds.yaml; all three are reported. Feeds evals/report.py.
"""

# TODO: load golden_set.jsonl, run 3 models, compute metrics, hand to report
