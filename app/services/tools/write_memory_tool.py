"""LLM tool: the EXPLICIT write_memory tool.

Per the brief there are NO auto-writes to long-term memory — the LLM must
deliberately call this tool. Dispatches into memory_service.write_long_term,
which appends the required audit-log row.
"""

# TODO: tool schema + run(user, content, memory_type)
