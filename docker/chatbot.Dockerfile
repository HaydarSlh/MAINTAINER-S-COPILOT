# Image for the `chatbot` service (Streamlit internal tool).

FROM python:3.11-slim
WORKDIR /srv
COPY pyproject.toml ./
# TODO: pip install ".[chatbot]" ; COPY chatbot/ ;
#       CMD streamlit run chatbot/app.py --server.port 8501
