"""Evals page — visualize classification and RAG eval results against committed gates.

Reads the JSON reports produced by `python -m evals.classification.run_eval`
and `python -m evals.rag.run_eval`, plus `eval_thresholds.yaml` (the CI gates).
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

st.set_page_config(page_title="Evals", page_icon="📊", layout="wide")

st.title("📊 Evals")
st.caption(
    "Committed thresholds in `eval_thresholds.yaml` are the CI gates. "
    "The api refuses to boot if any threshold is set to zero."
)

_ROOT = Path(__file__).resolve().parents[2]
_CLS_PATH = _ROOT / "eval_report_classification.json"
_RAG_PATH = _ROOT / "eval_report_rag.json"
_RAG_NAIVE_PATH = _ROOT / "eval_report_rag_naive.json"
_THR_PATH = _ROOT / "eval_thresholds.yaml"


def _load(path: Path):
    """Load a JSON or YAML file from disk, returning None if it does not exist."""
    if not path.exists():
        return None
    if path.suffix == ".yaml":
        return yaml.safe_load(path.read_text())
    return json.loads(path.read_text())


cls = _load(_CLS_PATH)
rag = _load(_RAG_PATH)
rag_naive = _load(_RAG_NAIVE_PATH)
thr = _load(_THR_PATH)

# ── Threshold gates dashboard ────────────────────────────────────────────────
st.header("Threshold gates")

if thr is None:
    st.error("eval_thresholds.yaml not found.")
else:
    gates: list[dict] = []

    if cls and thr.get("classification"):
        t = thr["classification"]
        ft = cls["models"].get("finetuned", {})
        gates.append({
            "Gate": "classification.macro_f1",
            "Threshold": t["macro_f1_min"],
            "Observed": ft.get("macro_f1", 0.0),
            "Status": "✅ PASS" if ft.get("macro_f1", 0.0) >= t["macro_f1_min"] else "❌ FAIL",
        })
        for cls_name, floor in (t.get("per_class_f1_min") or {}).items():
            obs = ft.get("per_class_f1", {}).get(cls_name, 0.0)
            gates.append({
                "Gate": f"classification.per_class_f1.{cls_name}",
                "Threshold": floor,
                "Observed": obs,
                "Status": "✅ PASS" if obs >= floor else "❌ FAIL",
            })

    if rag and thr.get("rag"):
        t = thr["rag"]
        ret = rag.get("retrieval", {})
        gates.append({
            "Gate": "rag.hit_at_5",
            "Threshold": t["hit_at_5_min"],
            "Observed": ret.get("hit_at_5", 0.0),
            "Status": "✅ PASS" if ret.get("hit_at_5", 0.0) >= t["hit_at_5_min"] else "❌ FAIL",
        })
        gates.append({
            "Gate": "rag.mrr_at_10",
            "Threshold": t["mrr_at_10_min"],
            "Observed": ret.get("mrr_at_10", 0.0),
            "Status": "✅ PASS" if ret.get("mrr_at_10", 0.0) >= t["mrr_at_10_min"] else "❌ FAIL",
        })

    if gates:
        st.dataframe(pd.DataFrame(gates), use_container_width=True, hide_index=True)
    else:
        st.info("No eval reports found yet. Run the eval suites to populate this page.")

# ── Classification ───────────────────────────────────────────────────────────
st.header("Classification")

if cls is None:
    st.warning(f"`{_CLS_PATH.name}` not found.")
else:
    st.caption(f"Golden set: {cls.get('golden_set_size', '?')} examples")

    rows = []
    for name, m in cls.get("models", {}).items():
        row = {"model": name, "macro_f1": m.get("macro_f1", 0.0)}
        for k, v in (m.get("per_class_f1") or {}).items():
            row[f"f1_{k}"] = v
        rows.append(row)
    if rows:
        st.subheader("Macro and per-class F1")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("Confusion matrices")
    cols = st.columns(len(cls.get("models", {})) or 1)
    for col, (name, m) in zip(cols, cls.get("models", {}).items()):
        cm = m.get("confusion_matrix")
        if not cm:
            continue
        df = pd.DataFrame(cm["matrix"], index=cm["labels"], columns=cm["labels"])
        df.index.name = "true ↓ / pred →"
        with col:
            st.markdown(f"**{name}**")
            st.dataframe(df, use_container_width=True)

# ── RAG retrieval ────────────────────────────────────────────────────────────
st.header("RAG retrieval")

if rag is None:
    st.warning(f"`{_RAG_PATH.name}` not found.")
else:
    st.caption(
        f"Golden set: {rag.get('golden_set_size', '?')} triples · "
        f"strategy={rag.get('config', {}).get('strategy', '?')} · "
        f"model={rag.get('config', {}).get('model', '?')}"
    )

    rows = []
    if rag:
        r = rag.get("retrieval", {})
        rows.append({
            "variant": rag.get("config", {}).get("strategy", "structure"),
            "hit@5": r.get("hit_at_5", 0.0),
            "MRR@10": r.get("mrr_at_10", 0.0),
            "n": r.get("n", 0),
        })
    if rag_naive:
        r = rag_naive.get("retrieval", {})
        rows.append({
            "variant": "naive (baseline)",
            "hit@5": r.get("hit_at_5", 0.0),
            "MRR@10": r.get("mrr_at_10", 0.0),
            "n": r.get("n", 0),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    chart_df = df.set_index("variant")[["hit@5", "MRR@10"]]
    st.bar_chart(chart_df)

    if rag.get("generation", {}).get("skipped"):
        st.info(
            "Generation metrics (RAGAS faithfulness / answer_relevancy) are not "
            "measured in offline CI. They require the live app stack with a real "
            "LLM — see DECISIONS.md D11."
        )
