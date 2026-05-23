"""Non-secret runtime configuration (ports, hostnames, feature flags).

Secrets are NOT here — they resolve from Vault at startup via app/infra/vault.py.
This module only reads the non-secret values allowed in .env (ports + service
coordinates) per the brief's secrets policy.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Vault locator (token itself is the only secret allowed in .env)
    vault_addr: str = "http://vault:8200"
    vault_dev_root_token: str = ""

    # Service coordinates (non-secret hostnames inside the compose network)
    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "copilot"
    redis_host: str = "redis"
    redis_port: int = 6379
    minio_endpoint: str = "minio:9000"
    modelserver_url: str = "http://modelserver:8001"

    api_port: int = 8000

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()  # imported wherever non-secret config is needed
