"""Memory business logic — short-term (Redis) + long-term (pgvector).

Short-term: conversation state in Redis with an explicit, justified TTL.
Long-term: written ONLY via the explicit write_memory tool (no auto-writes);
every long-term write also appends an audit-log row (actor, action, target,
timestamp). Owns memory invalidation. Powers the Friday cross-conversation
recall demo and the Streamlit memory inspector.
"""

# TODO: get_short_term, set_short_term(ttl), write_long_term (-> audit),
#       recall(user, query) for cross-conversation memory
