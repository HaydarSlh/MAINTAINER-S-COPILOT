"""Embed route + public widget config.

GET /widget.js             — loader script; host pastes one <script> tag,
                             the loader injects the iframe pointing at /embed/{id}
GET /embed/config/{id}     — public widget config (theme, greeting, tools)
                             + CSP frame-ancestors header from DB allowed_origins
                             + CORS Allow-Origin header restricted to allowed_origins

Origin allowlisting is enforced from DB, NOT env (brief requirement).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

router = APIRouter(tags=["embed"])

# Loader script: injected into the host page via <script data-widget-id="...">
# It creates an iframe pointing to the widget bundle served on Friday (React).
_WIDGET_JS = """\
(function () {
  var s = document.currentScript;
  var widgetId = s && s.getAttribute('data-widget-id');
  if (!widgetId) { console.error('[copilot-widget] data-widget-id missing'); return; }
  var iframe = document.createElement('iframe');
  iframe.src = s.src.replace('/widget.js', '/embed/' + widgetId);
  iframe.style.cssText = 'position:fixed;bottom:24px;right:24px;width:380px;height:560px;border:none;z-index:2147483647;';
  iframe.allow = 'clipboard-write';
  document.body.appendChild(iframe);
})();
"""


@router.get("/widget.js", response_class=PlainTextResponse)
async def widget_js() -> PlainTextResponse:
    return PlainTextResponse(
        content=_WIDGET_JS,
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/embed/config/{widget_id}")
async def embed_config(widget_id: str, request: Request) -> JSONResponse:
    from app.services.widget_service import get_public_config

    config = await get_public_config(widget_id)
    if config is None:
        return JSONResponse(status_code=404, content={"error": "Widget not found"})

    # Origin allowlisting — enforced from DB, not env
    origins = config.allowed_origins
    csp = "frame-ancestors " + " ".join(origins) if origins else "frame-ancestors 'none'"

    # Respect the request Origin for CORS; only allow if it's in the DB list
    request_origin = request.headers.get("origin", "")
    cors_origin = request_origin if request_origin in origins else ""

    headers = {
        "Content-Security-Policy": csp,
        "X-Frame-Options": "ALLOWALL",  # CSP takes precedence; this is a fallback hint
    }
    if cors_origin:
        headers["Access-Control-Allow-Origin"] = cors_origin
        headers["Vary"] = "Origin"

    return JSONResponse(
        content={
            "widget_id": config.widget_id,
            "theme": config.theme,
            "greeting": config.greeting,
            "enabled_tools": config.enabled_tools,
        },
        headers=headers,
    )
