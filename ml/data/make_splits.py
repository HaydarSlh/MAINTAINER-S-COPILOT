"""Build train/val/test splits.

Per the brief: splits are stratified by label AND the test set is strictly
more recent in time than train (temporal split — no future leakage). Records
the training-data hash used in the model card.
"""

# TODO: make_splits(issues) -> (train, val, test) + dataset hash
