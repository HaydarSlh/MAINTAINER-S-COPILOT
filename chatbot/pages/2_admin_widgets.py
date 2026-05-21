"""Admin-only widget configuration page."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(page_title="Widgets — Admin", page_icon="⚙️", layout="wide")

# ── Auth + role gate ──────────────────────────────────────────────────────────
if "token" not in st.session_state:
    st.warning("Please sign in first.")
    st.stop()

user: dict = st.session_state["user"]
if user.get("role") != "admin":
    st.error("Admin access required.")
    st.stop()

import json
import api_client

token: str = st.session_state["token"]

st.title("Widget Configuration")

# ── Existing widgets ──────────────────────────────────────────────────────────
st.subheader("Active widgets")
try:
    widgets = api_client.list_widgets(token)
except Exception as exc:
    st.error(f"Could not load widgets: {exc}")
    widgets = []

if not widgets:
    st.info("No widgets yet. Create one below.")
else:
    for w in widgets:
        with st.expander(f"Widget `{w['widget_id']}`"):
            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown(f"**Greeting:** {w['greeting']}")
                st.markdown(f"**Enabled tools:** {', '.join(w['enabled_tools'])}")
                st.markdown(f"**Allowed origins:**")
                for o in w["allowed_origins"]:
                    st.code(o)
            with col_r:
                if st.button("Get embed snippet", key=f"snip_{w['widget_id']}"):
                    try:
                        snippet = api_client.get_snippet(token, w["widget_id"])
                        st.code(snippet, language="html")
                    except Exception as exc:
                        st.error(str(exc))

            # Inline edit form
            with st.form(f"edit_{w['widget_id']}"):
                st.caption("Edit widget")
                new_greeting = st.text_input("Greeting", value=w["greeting"])
                new_origins_raw = st.text_area(
                    "Allowed origins (one per line)",
                    value="\n".join(w["allowed_origins"]),
                )
                all_tools = ["classify_issue", "extract_entities",
                             "search_docs", "summarize_issue", "write_memory"]
                new_tools = st.multiselect(
                    "Enabled tools",
                    options=all_tools,
                    default=w["enabled_tools"],
                )
                if st.form_submit_button("Save changes"):
                    new_origins = [o.strip() for o in new_origins_raw.splitlines() if o.strip()]
                    try:
                        api_client.update_widget(token, w["widget_id"], {
                            "greeting": new_greeting,
                            "allowed_origins": new_origins,
                            "enabled_tools": new_tools,
                        })
                        st.success("Saved.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

# ── Create new widget ─────────────────────────────────────────────────────────
st.divider()
st.subheader("Create new widget")

with st.form("create_widget"):
    origins_raw = st.text_area(
        "Allowed origins (one per line)",
        placeholder="https://example.com\nhttps://docs.example.com",
    )
    greeting = st.text_input("Greeting", value="How can I help?")
    all_tools = ["classify_issue", "extract_entities",
                 "search_docs", "summarize_issue", "write_memory"]
    enabled_tools = st.multiselect(
        "Enabled tools",
        options=all_tools,
        default=["classify_issue", "search_docs", "summarize_issue"],
    )
    theme_raw = st.text_area("Theme JSON (optional)", value="{}")
    submitted = st.form_submit_button("Create widget")

if submitted:
    origins = [o.strip() for o in origins_raw.splitlines() if o.strip()]
    if not origins:
        st.error("At least one allowed origin is required.")
    else:
        try:
            theme = json.loads(theme_raw or "{}")
        except json.JSONDecodeError:
            st.error("Theme must be valid JSON.")
            st.stop()
        try:
            new_w = api_client.create_widget(token, {
                "allowed_origins": origins,
                "greeting": greeting,
                "enabled_tools": enabled_tools,
                "theme": theme,
            })
            st.success(f"Widget `{new_w['widget_id']}` created.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
