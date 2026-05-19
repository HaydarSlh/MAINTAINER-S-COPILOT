"""Chat route: authenticated message -> streamed reply.

Thin: validate, call chat_service.handle_message, stream the response. The
tool-calling, memory, and tracing all happen in the service layer.
"""

# TODO: POST /chat (auth required), streaming response
