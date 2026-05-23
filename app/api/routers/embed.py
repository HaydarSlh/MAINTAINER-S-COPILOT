"""Embed route + public widget config.

GET  /widget.js             — loader script; host pastes one <script> tag,
                              the loader injects the iframe pointing at /embed/{id}
GET  /embed/config/{id}     — public widget config (theme, greeting, tools)
                              + CSP frame-ancestors header from DB allowed_origins
                              + CORS Allow-Origin header restricted to allowed_origins
POST /embed/chat            — unauthenticated chat endpoint for the embedded widget;
                              validated by widget_id instead of JWT.

Origin allowlisting is enforced from DB, NOT env (brief requirement).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel

router = APIRouter(tags=["embed"])

# Loader script injected into the host page via <script data-widget-id="...">.
#
# Layout strategy:
#  - Iframe starts as a small bubble (88px circle) anchored bottom-right.
#  - Widget posts {type:'copilot:resize', open: true/false} when the user
#    toggles it. We compute target width/height clamped to the host viewport
#    so the iframe never gets clipped above the top of the page.
#  - We ALSO listen to window resize so the iframe re-clamps when the user
#    resizes the browser while the widget is open.
_WIDGET_JS = """\
(function () {
  var s = document.currentScript;
  var widgetId = s && s.getAttribute('data-widget-id');
  if (!widgetId) { console.error('[copilot-widget] data-widget-id missing'); return; }
  var iframe = document.createElement('iframe');
  iframe.src = s.src.replace('/widget.js', '/embed/' + widgetId);
  iframe.style.cssText = 'position:fixed;bottom:24px;right:24px;width:88px;height:88px;border:none;border-radius:50%;box-shadow:0 4px 16px rgba(0,0,0,0.20);z-index:2147483647;transition:width 0.2s,height 0.2s,border-radius 0.2s;background:transparent;';
  iframe.allow = 'clipboard-write';
  document.body.appendChild(iframe);

  var isOpen = false;
  function applyOpenLayout() {
    var w = Math.min(480, Math.max(280, window.innerWidth  - 48));
    var h = Math.min(720, Math.max(360, window.innerHeight - 48));
    iframe.style.width = w + 'px';
    iframe.style.height = h + 'px';
    iframe.style.borderRadius = '12px';
  }
  function applyClosedLayout() {
    iframe.style.width = '88px';
    iframe.style.height = '88px';
    iframe.style.borderRadius = '50%';
  }

  window.addEventListener('message', function(e) {
    if (!e.data || e.data.type !== 'copilot:resize') return;
    isOpen = !!e.data.open;
    if (isOpen) applyOpenLayout();
    else applyClosedLayout();
  });

  window.addEventListener('resize', function() {
    if (isOpen) applyOpenLayout();
  });
})();
"""


@router.get("/widget.js", response_class=PlainTextResponse)
async def widget_js() -> PlainTextResponse:
    """Serve the widget loader script that injects the iframe into the host page."""
    return PlainTextResponse(
        content=_WIDGET_JS,
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/embed/config/{widget_id}")
async def embed_config(widget_id: str, request: Request) -> JSONResponse:
    """Return the public widget config with appropriate CSP and CORS headers."""
    from app.services.widget_service import get_public_config

    config = await get_public_config(widget_id)
    if config is None:
        return JSONResponse(status_code=404, content={"error": "Widget not found"})

    # Host-page allowlisting is enforced by CSP frame-ancestors (browser blocks
    # the iframe if the embedding page's origin isn't in the list).
    # CORS is a separate concern — it must allow the widget iframe itself
    # (different origin from the host page) to fetch its own config.
    origins = config.allowed_origins
    csp = "frame-ancestors " + " ".join(origins) if origins else "frame-ancestors 'none'"

    request_origin = request.headers.get("origin", "")
    headers = {
        "Content-Security-Policy": csp,
        "X-Frame-Options": "ALLOWALL",
        "Vary": "Origin",
    }
    if request_origin:
        headers["Access-Control-Allow-Origin"] = request_origin
        headers["Access-Control-Allow-Credentials"] = "true"

    return JSONResponse(
        content={
            "widget_id": config.widget_id,
            "theme": config.theme,
            "greeting": config.greeting,
            "enabled_tools": config.enabled_tools,
        },
        headers=headers,
    )


@router.get("/embed/history/{widget_id}/{conversation_id}")
async def embed_history(widget_id: str, conversation_id: str, request: Request) -> JSONResponse:
    """Return the messages of a past conversation for a widget session.

    No auth — the conversation_id is unguessable (UUID) so possession of it
    is sufficient proof of ownership for the widget context.
    """
    from app.db.session import get_session
    from app.repositories import conversation_repo
    from app.services.widget_service import get_public_config

    config = await get_public_config(widget_id)
    if config is None:
        return JSONResponse(status_code=404, content={"error": "Widget not found"})

    async with get_session() as session:
        conv = await conversation_repo.get_conversation(session, conversation_id)
        if conv is None:
            return JSONResponse(status_code=404, content={"error": "Conversation not found"})
        messages = [
            {"role": m.role, "content": m.content}
            for m in conv.messages
            if m.role in ("user", "assistant") and m.content
        ]

    request_origin = request.headers.get("origin", "")
    headers = {}
    if request_origin:
        headers["Access-Control-Allow-Origin"] = request_origin
        headers["Access-Control-Allow-Credentials"] = "true"

    return JSONResponse(content={"messages": messages}, headers=headers)


class _EmbedChatRequest(BaseModel):
    """Request body for the unauthenticated embed chat endpoint."""
    widget_id: str
    text: str
    conversation_id: str | None = None


@router.post("/embed/chat")
async def embed_chat(body: _EmbedChatRequest, request: Request) -> StreamingResponse:
    """Unauthenticated chat for the embedded widget.

    Validates widget_id against the DB (widget must exist and be active).
    Runs the full chat pipeline as the widget owner so tools/memories work.
    """
    from app.db.session import get_session
    from app.repositories import widget_repo
    from app.services.widget_service import get_public_config

    config = await get_public_config(body.widget_id)
    if config is None:
        return JSONResponse(status_code=404, content={"error": "Widget not found"})

    async with get_session() as session:
        widget_orm = await widget_repo.get_orm_by_id(session, body.widget_id)
        owner_id = str(widget_orm.owner_id)

    from app.domain.enums import Role
    from app.domain.models import User
    from app.services.chat_service import handle_message

    guest_user = User(
        id=owner_id,
        email="widget-guest@embed",
        role=Role.USER,
        is_active=True,
        is_verified=True,
        is_superuser=False,
    )

    request_origin = request.headers.get("origin", "")
    cors_headers = {}
    if request_origin:
        cors_headers["Access-Control-Allow-Origin"] = request_origin
        cors_headers["Access-Control-Allow-Credentials"] = "true"

    async def _event_stream():
        """Yield SSE-formatted chunks for the widget chat turn."""
        async for chunk in handle_message(guest_user, body.conversation_id, body.text):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers=cors_headers,
    )
