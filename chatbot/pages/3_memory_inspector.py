"""Memory inspector — long-term memories + audit log.

Supports the cross-conversation recall demo: shows what the LLM remembers
about the user and lets them delete entries. Audit log is admin-only.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(page_title="Memory — Maintainer's Copilot", page_icon="🧠", layout="wide")

# ── Auth gate ─────────────────────────────────────────────────────────────────
if "token" not in st.session_state:
    st.warning("Please sign in first.")
    st.stop()

import api_client

token: str = st.session_state["token"]
user: dict = st.session_state["user"]
is_admin: bool = user.get("role") == "admin"

st.title("Memory Inspector")

# ── Long-term memories ────────────────────────────────────────────────────────
st.subheader("Your long-term memories")
st.caption(
    "These are saved only when you explicitly ask the copilot to remember something. "
    "Delete any entry you no longer want."
)

try:
    memories = api_client.get_memories(token)
except Exception as exc:
    st.error(f"Could not load memories: {exc}")
    memories = []

if not memories:
    st.info("No long-term memories saved yet.")
else:
    _TYPE_ICON = {"episodic": "📅", "semantic": "📚", "procedural": "⚙️"}
    for mem in memories:
        icon = _TYPE_ICON.get(mem.get("type", ""), "💾")
        col_text, col_del = st.columns([10, 1])
        with col_text:
            st.markdown(f"{icon} **{mem.get('type', 'unknown')}** — {mem['content']}")
        with col_del:
            if st.button("🗑", key=f"del_{mem['id']}", help="Delete this memory"):
                try:
                    api_client.delete_memory(token, mem["id"])
                    st.success("Deleted.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

# ── Audit log (admin only) ────────────────────────────────────────────────────
if is_admin:
    st.divider()
    st.subheader("Audit log")
    st.caption("Append-only record of all writes, role changes, and widget updates.")

    limit = st.slider("Entries to show", min_value=10, max_value=500, value=100, step=10)

    try:
        entries = api_client.get_audit_log(token, limit=limit)
    except Exception as exc:
        st.error(f"Could not load audit log: {exc}")
        entries = []

    if not entries:
        st.info("Audit log is empty.")
    else:
        import pandas as pd
        df = pd.DataFrame(entries)[["created_at", "actor_id", "action", "target_type", "target_id", "detail"]]
        df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        st.dataframe(df, use_container_width=True, hide_index=True)
