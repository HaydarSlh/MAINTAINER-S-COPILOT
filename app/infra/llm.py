"""LLM provider adapter — the single tool-calling LLM.

The chatbot is ONE tool-calling LLM (not a workflow, not multi-agent). This
adapter wraps the provider SDK, exposes tool-calling, and emits a span per LLM
call (model name, token counts, latency, redacted inputs/outputs). API key
comes from Vault. Provider/model choice recorded in DECISIONS.md D12.
"""

# TODO: provider client from Vault-resolved key
# TODO: chat(messages, tools) -> tool calls / content, wrapped in a trace span
# TODO: token + latency capture for span attributes


def chat(messages: list[dict], tools: list[dict]):
    raise NotImplementedError
