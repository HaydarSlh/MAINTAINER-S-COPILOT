"""Issue classification business logic.

Calls the deployed classifier via the modelserver HTTP client (the deployment
choice among classical/fine-tuned/LLM is defended in DECISIONS.md D3). Wraps
the result in a domain Classification. The tool layer exposes this to the LLM.
"""

# TODO: classify_issue(text) -> domain.Classification (handles modelserver down)
