"""Map maintainer-applied labels -> {bug, feature, docs, question}.

This mapping is a judgment call defended in DECISIONS.md D1. Ambiguous labels
are dropped rather than guessed. Single source of truth for the mapping used
by both training and the golden set.
"""

# TODO: LABEL_MAP dict + map_labels(raw_labels) -> IssueLabel | None
