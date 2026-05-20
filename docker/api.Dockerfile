# Image for the `api` service (FastAPI: auth, chat, memory, RAG, widget config).
# No torch / streamlit — stays lean. Secrets resolved from Vault at boot.

FROM python:3.11-slim
WORKDIR /srv

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir "."

COPY app/ app/
COPY prompts/ prompts/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
