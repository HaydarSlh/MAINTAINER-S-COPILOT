"""MinIO adapter — blob storage for model artifacts, eval reports, chunk snapshots.

Credentials resolve from Vault (secret/minio). Falls back to env vars for
running outside the compose stack.

Stores:
  - models/            model artifacts (weights, tokenizer, classical pipeline)
  - evals/             eval_report.json from every CI run
  - rag_snapshots/     per-conversation retrieved-chunk snapshots (last N)
"""

from __future__ import annotations

import io
import json
import os
from functools import lru_cache


def _creds() -> tuple[str, str, str]:
    """Return (endpoint, access_key, secret_key)."""
    try:
        from app.infra.vault import read_secret
        s = read_secret("secret/data/minio")
        return (
            os.environ.get("MINIO_ENDPOINT", "localhost:9000"),
            s.get("access_key", "minioadmin"),
            s.get("secret_key", "minioadmin"),
        )
    except Exception:
        return (
            os.environ.get("MINIO_ENDPOINT", "localhost:9000"),
            os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
            os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
        )


@lru_cache(maxsize=1)
def _client():
    """Return the cached MinIO client instance."""
    from minio import Minio
    endpoint, access_key, secret_key = _creds()
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)


def ensure_bucket(bucket: str) -> None:
    """Create the bucket if it does not already exist."""
    client = _client()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def put_object(bucket: str, key: str, data: io.BytesIO, length: int,
               content_type: str = "application/octet-stream") -> None:
    """Upload an in-memory BytesIO object to the specified bucket and key."""
    ensure_bucket(bucket)
    _client().put_object(bucket, key, data, length, content_type=content_type)


def get_object(bucket: str, key: str) -> bytes:
    """Download and return the raw bytes of an object from MinIO."""
    resp = _client().get_object(bucket, key)
    return resp.read()


def fput_object(bucket: str, key: str, file_path: str) -> None:
    """Upload a local file to MinIO by path."""
    ensure_bucket(bucket)
    _client().fput_object(bucket, key, file_path)


def object_exists(bucket: str, key: str) -> bool:
    """Return True if the object exists in MinIO, False otherwise."""
    try:
        _client().stat_object(bucket, key)
        return True
    except Exception:
        return False


# ── Eval report ───────────────────────────────────────────────────────────────

def put_eval_report(report: dict, key: str = "classification/eval_report.json") -> None:
    """Serialize and upload an eval report dict to the evals bucket."""
    data = json.dumps(report, indent=2).encode()
    put_object("evals", key, io.BytesIO(data), len(data), content_type="application/json")


def get_previous_green_report(key: str = "classification/eval_report.json") -> dict | None:
    """Fetch the last committed eval report from MinIO, or None if absent."""
    try:
        return json.loads(get_object("evals", key).decode())
    except Exception:
        return None


# ── Chunk snapshot ─────────────────────────────────────────────────────────────

def put_chunk_snapshot(conversation_id: str, chunks: list[dict]) -> None:
    """Persist a timestamped snapshot of retrieved RAG chunks to MinIO for debugging."""
    import time
    payload = json.dumps({
        "conversation_id": conversation_id,
        "ts": int(time.time()),
        "chunks": chunks,
    }, ensure_ascii=False).encode()
    key = f"rag_snapshots/{conversation_id}/{int(time.time())}.json"
    put_object("evals", key, io.BytesIO(payload), len(payload), content_type="application/json")


# ── Model artifact ─────────────────────────────────────────────────────────────

def get_model_artifact(object_key: str, dest_path: str) -> None:
    """Download a model artifact from MinIO to a local path."""
    _client().fget_object("models", object_key, dest_path)
