"""Chat orchestration — drives the single tool-calling LLM.

One LLM that picks tools (NOT a workflow, NOT multi-agent). Responsibilities:
  - load the versioned system prompt from prompts/,
  - assemble context: short-term state (Redis) + relevant long-term memory,
  - call the LLM with the tool schemas (app/services/tools/),
  - execute chosen tools, catching ToolFailure so the bot degrades gracefully
    (e.g. classifier down -> says so, falls back, does NOT 500),
  - root the conversation trace tree; each LLM/tool call is a child span.
"""

# TODO: handle_message(user, conversation_id, text) -> reply (streamed)
