"""Memory routes: inspect long-term memory, list audit entries.

Powers the Streamlit memory inspector. Writes happen only via the LLM's
explicit write_memory tool — there is no auto-write endpoint here.
"""

# TODO: GET /memory (auth), GET /memory/audit (admin)
