"""Long-term memory persistence — Postgres + pgvector. SQL only.

Stores memory records with an embedding column for similarity search. The
memory TYPE (episodic/semantic/procedural) is chosen + defended in
DECISIONS.md D8. Writes are only ever triggered by the explicit write_memory
tool (no auto-writes) and always paired with an audit-log row by the service.
"""

# TODO: insert_memory(record, embedding), search(user_id, query_embedding, k)
