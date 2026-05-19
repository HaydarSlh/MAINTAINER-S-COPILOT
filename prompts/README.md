# prompts/

Per the brief: prompts are files here, version-controlled. Loaded by the
service layer at runtime; never inlined in code. Changing a prompt is a
reviewable diff.

- `chatbot_system.md` — system prompt for the single tool-calling LLM
- `summarizer.md` — summarization prompt (if LLM-driven)
- `llm_classifier_baseline.md` — prompt for the LLM classification baseline
- `query_rewrite.md` — RAG query-transformation prompt
