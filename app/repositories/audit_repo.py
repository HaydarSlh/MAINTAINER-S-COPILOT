"""Audit-log persistence. SQL only.

Per the brief, an audit-log row (actor, action, target, timestamp) is written
for: role changes, memory writes, widget config changes, conversation
deletions. Append-only; never updated or deleted.
"""

# TODO: append(actor, action, target, timestamp), list(filters)
