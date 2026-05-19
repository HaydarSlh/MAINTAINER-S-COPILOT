"""MinIO blob adapter.

Per the brief, MinIO holds: model artifacts (or a manifest), eval_report.json
from every CI run, training plots, and per-conversation retrieved-chunks
snapshots for the last N conversations. Credentials come from Vault.
"""

# TODO: minio.Minio client built from Vault-resolved credentials
# TODO: put_eval_report(), get_previous_green_report() (for CI diff)
# TODO: put_chunk_snapshot(conversation_id, chunks)
# TODO: get_model_artifact() / manifest accessor


def put_eval_report(report: dict) -> None:
    raise NotImplementedError
