"""Chat route: authenticated message → streamed reply (SSE).

POST /chat  — sends a message, streams the assistant reply as SSE text/event-stream.
             First event carries [conv:<id>] so the client knows the conversation ID.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.domain.models import User

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    """Request body for the /chat endpoint."""
    text: str
    conversation_id: str | None = None


@router.post("/chat")
async def chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Stream the assistant reply to a user message as SSE."""
    from app.services.chat_service import handle_message

    async def _event_stream():
        """Yield SSE-formatted chunks for the full assistant turn."""
        async for chunk in handle_message(user, body.conversation_id, body.text):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(_event_stream(), media_type="text/event-stream")
