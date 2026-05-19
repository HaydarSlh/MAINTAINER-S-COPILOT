"""Write the classifier model card.

Per the brief the card lists: architecture, hyperparameters, training-data
hash, and final metrics. The card's SHA-256 of the weights is what both the
api and modelserver assert at boot (refuse-to-boot on mismatch).
"""

# TODO: write(path, arch, hparams, data_hash, metrics, weights_sha256)
