# Infra layer: adapters for Vault, MinIO, Redis, LLM providers, the model
# server, the tracing backend, and the redaction layer. Only this layer talks
# to the outside world. Services depend on these; the API layer never does.
