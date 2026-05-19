# Image for the `api` service (FastAPI: auth, chat, memory, RAG, widget config).
# Installs only core deps (no torch/streamlit) to stay lean.
# TODO: python:3.11-slim, pip install ".", uvicorn app.main:app

FROM python:3.11-slim
WORKDIR /srv
COPY pyproject.toml ./
# TODO: pip install . ; COPY app/ ; CMD uvicorn app.main:app --host 0.0.0.0
