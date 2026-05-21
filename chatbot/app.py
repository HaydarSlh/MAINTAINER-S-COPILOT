"""Streamlit entrypoint: login gate + page navigation.

Session state keys:
  token      — JWT string (set on successful login/register)
  user       — {id, email, role} dict
  conv_id    — active conversation ID (set by chat page on first message)
"""

import streamlit as st

st.set_page_config(
    page_title="Maintainer's Copilot",
    page_icon="🔧",
    layout="centered",
)


def _login_form() -> None:
    st.title("Maintainer's Copilot")
    st.caption("Sign in to continue")

    tab_login, tab_register = st.tabs(["Sign in", "Register"])

    with tab_login:
        with st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in")

        if submitted:
            if not email or not password:
                st.error("Email and password are required.")
                return
            try:
                import api_client
                data = api_client.login(email, password)
                st.session_state["token"] = data["access_token"]
                st.session_state["user"] = data["user"]
                st.rerun()
            except Exception as exc:
                st.error(f"Login failed: {exc}")

    with tab_register:
        with st.form("register"):
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_pw")
            reg_submitted = st.form_submit_button("Create account")

        if reg_submitted:
            if not reg_email or not reg_password:
                st.error("Email and password are required.")
                return
            try:
                import api_client
                data = api_client.register(reg_email, reg_password)
                st.session_state["token"] = data["access_token"]
                st.session_state["user"] = data["user"]
                st.rerun()
            except Exception as exc:
                st.error(f"Registration failed: {exc}")


def _home() -> None:
    user = st.session_state["user"]
    st.title("Maintainer's Copilot")
    st.write(f"Signed in as **{user['email']}** ({user['role']})")
    st.markdown(
        "Use the sidebar to navigate:\n"
        "- **Chat** — triage issues and ask pydantic questions\n"
        "- **Memory Inspector** — review and delete long-term memories\n"
        + ("- **Admin: Widgets** — manage embed widget configs\n" if user["role"] == "admin" else "")
    )

    if st.button("Sign out"):
        for key in ("token", "user", "conv_id"):
            st.session_state.pop(key, None)
        st.rerun()


# ── Gate ──────────────────────────────────────────────────────────────────────

if "token" not in st.session_state:
    _login_form()
else:
    _home()
