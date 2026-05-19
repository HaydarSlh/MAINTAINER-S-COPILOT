# Tool definitions the single tool-calling LLM picks among. Each tool wraps a
# service (classifier, NER, summarizer, RAG) or is the explicit write_memory
# tool. Tools are thin: schema + call into the service layer. Failures raise
# ToolFailure so the chat service can degrade gracefully.
