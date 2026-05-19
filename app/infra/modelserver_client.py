"""HTTP client to the `modelserver` service (classifier / NER / summarizer).

Per the brief these pipelines live behind FastAPI endpoints the chatbot calls
OVER HTTP — not imported in-process. If modelserver is down this raises, and
the chat service degrades gracefully (the bot says so, does not 500).
Each call is a trace span.
"""

# TODO: httpx.AsyncClient targeting settings.modelserver_url
# TODO: classify(text), extract_entities(text), summarize(text)


async def classify(text: str) -> dict:
    raise NotImplementedError
