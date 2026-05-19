"""Three-way comparison -> the deployment decision.

Runs classical / fine-tuned / LLM on the same test split and produces the
DECISIONS.md D3 table: accuracy, macro-F1, per-class F1, latency, cost. The
deployment choice is argued from these numbers (best F1 is not automatically
the deploy choice once latency/cost/failure-cost are weighed).
"""

# TODO: run_all() -> comparison table; emit markdown for DECISIONS.md
