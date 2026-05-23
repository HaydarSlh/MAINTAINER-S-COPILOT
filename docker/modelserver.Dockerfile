# Image for the `modelserver` service (classifier / NER / summarizer).
# Heavy ML deps installed via .[modelserver] — torch lives only here.
# Refuses to boot if classifier weights are missing or SHA-256 mismatches.

FROM python:3.11-slim
WORKDIR /srv

# torch layer is large — install before copying code so Docker cache reuses it
COPY pyproject.toml README.md ./
# Install CPU-only torch first to avoid pulling 2 GB of CUDA wheels
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir ".[modelserver]"

COPY modelserver/ modelserver/
COPY app/artifacts/ app/artifacts/

EXPOSE 8001
CMD ["uvicorn", "modelserver.main:app", "--host", "0.0.0.0", "--port", "8001"]
