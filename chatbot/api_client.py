"""Thin HTTP client to the FastAPI `api` service.

The Streamlit app holds NO business logic and never touches the DB/Redis — it
calls api endpoints (auth, chat, memory, widgets) over HTTP with the user's
JWT.
"""

# TODO: login, chat, get_memory, list_audit, widget CRUD wrappers
