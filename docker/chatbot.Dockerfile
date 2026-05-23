# Image for the `chatbot` service (Streamlit internal tool).
# Admin config, memory inspector, full chat UI — not exposed publicly.

FROM python:3.11-slim
WORKDIR /srv

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir ".[chatbot]"

COPY chatbot/ chatbot/
COPY eval_thresholds.yaml ./
COPY eval_report_classification.json ./
COPY eval_report_rag.json ./
COPY eval_report_rag_naive.json ./

EXPOSE 8501
CMD ["streamlit", "run", "chatbot/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
