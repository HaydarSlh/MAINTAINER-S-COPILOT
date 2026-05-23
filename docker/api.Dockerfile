# Image for the `api` service (FastAPI: auth, chat, memory, RAG, widget config).
# No torch / streamlit — stays lean. Secrets resolved from Vault at boot.

FROM python:3.11-slim
WORKDIR /srv

COPY pyproject.toml README.md ./
# CPU-only torch first to avoid pulling ~2 GB of CUDA wheels
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir ".[rag]"

COPY app/ app/
COPY rag/ rag/
COPY prompts/ prompts/
COPY eval_thresholds.yaml ./
COPY corpus.jsonl ./

# Pre-download embedding + reranker models so first chat request is fast
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('multi-qa-mpnet-base-dot-v1'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
