# Image for the `modelserver` service (classifier / NER / summarizer).
# Heavy ML deps live ONLY here (.[modelserver]) so other images stay lean.

FROM python:3.11-slim
WORKDIR /srv
COPY pyproject.toml ./
# TODO: pip install ".[modelserver]" ; COPY modelserver/ ;
#       CMD uvicorn modelserver.main:app --host 0.0.0.0 --port 8001
