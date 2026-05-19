"""Modelserver non-secret config (port, artifact location).

Like the api, any secret needed here resolves from Vault — not from .env.
The classifier weights path / MinIO manifest reference lives here.
"""

from pydantic_settings import BaseSettings


class ModelServerSettings(BaseSettings):
    modelserver_port: int = 8001
    # Where the fine-tuned classifier artifact is fetched from (MinIO manifest).
    artifact_manifest: str = "models/classifier/manifest.json"

    class Config:
        env_file = ".env"


settings = ModelServerSettings()
