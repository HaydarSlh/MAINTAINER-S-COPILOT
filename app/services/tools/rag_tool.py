"""LLM tool: answer a maintainer question via the advanced RAG pipeline.

Dispatches into rag_service. Returns answer + cited chunks. Wraps failures as
ToolFailure.
"""

# TODO: tool schema + run(question, filters)
