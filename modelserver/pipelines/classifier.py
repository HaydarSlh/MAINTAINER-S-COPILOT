"""Fine-tuned encoder classifier — load + predict.

Loads the artifact (fetched via MinIO manifest), verifies SHA-256 against the
model card before serving, and predicts the 4-class label. The model card
(architecture, hyperparameters, training-data hash, final metrics) is produced
by ml/train/model_card.py.
"""

# TODO: load_model() (SHA-checked), predict(text) -> (label, confidence)
