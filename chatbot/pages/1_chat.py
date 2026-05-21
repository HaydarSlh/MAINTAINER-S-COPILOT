"""Authenticated chat page — streams replies from POST /chat."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(page_title="Chat — Maintainer's Copilot", page_icon="💬", layout="wide")

# ── Auth gate ─────────────────────────────────────────────────────────────────
if "token" not in st.session_state:
    st.warning("Please sign in first.")
    st.stop()

import api_client

token: str = st.session_state["token"]
user: dict = st.session_state["user"]

# ── Session state defaults ────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state["messages"] = []   # [{role, content}]
if "conv_id" not in st.session_state:
    st.session_state["conv_id"] = None

# ── Header ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([6, 1])
with col1:
    st.title("Chat")
with col2:
    if st.button("New chat"):
        st.session_state["messages"] = []
        st.session_state["conv_id"] = None
        st.rerun()

# ── Render history ────────────────────────────────────────────────────────────
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Input ─────────────────────────────────────────────────────────────────────
user_input = st.chat_input("Paste an issue or ask a pydantic question…")

if user_input:
    # Show user message immediately
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Stream assistant reply
    with st.chat_message("assistant"):
        placeholder = st.empty()
        collected = ""
        conv_id = st.session_state.get("conv_id")

        try:
            for chunk in api_client.chat_stream(token, user_input, conv_id):
                if chunk == "[DONE]":
                    break
                # First chunk carries conversation ID
                if chunk.startswith("[conv:") and chunk.endswith("]"):
                    st.session_state["conv_id"] = chunk[6:-1]
                    continue
                collected += chunk
                placeholder.markdown(collected + "▌")

            placeholder.markdown(collected)
            st.session_state["messages"].append({"role": "assistant", "content": collected})

        except Exception as exc:
            error_msg = f"Error: {exc}"
            placeholder.error(error_msg)
            st.session_state["messages"].append({"role": "assistant", "content": error_msg})
