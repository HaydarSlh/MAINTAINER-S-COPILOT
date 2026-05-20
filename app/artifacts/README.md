# app/artifacts/

This folder holds the **committed** model artifacts — i.e. the metadata that
lives in version control. The **weights themselves are NOT committed**; they
live in MinIO blob storage and are fetched at container startup.

## What lives here

| File | Purpose |
|------|---------|
| `model_card.json` | Architecture, hyperparameters, training-data hash, test metrics, and the SHA-256 of the weights file. Produced by the Colab training notebook (Section 11) and committed after every training run. |
| `manifest.json` | MinIO object paths for each artifact (weights, tokenizer config). Read by the modelserver at boot to know what to fetch. |

## Integrity guarantee

At startup, `modelserver` and `api` both assert:

```python
actual_sha = hashlib.sha256(open(weights_path, 'rb').read()).hexdigest()
assert actual_sha == model_card['weights_sha256'], "SHA mismatch — weights tampered or stale"
```

If the hash does not match, the service **refuses to boot**. This is a
committed requirement in the brief.

## Workflow

1. Train in Colab (`notebooks/training.ipynb`)
2. Notebook writes `model_card.json` to Drive
3. Copy `model_card.json` here and commit it
4. Upload weights to MinIO (Section 12 of the notebook)
5. Update `manifest.json` with the MinIO object path
