"""Widget config routes — admin-only CRUD + embed snippet.

POST   /widgets              — create a new widget config
PUT    /widgets/{id}         — update an existing widget config
GET    /widgets              — list all active widget configs
GET    /widgets/{id}/snippet — return the <script> embed tag
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.deps import require_admin
from app.domain.models import User, WidgetConfig

router = APIRouter(tags=["widgets"])


class CreateWidgetRequest(BaseModel):
    allowed_origins: list[str]
    theme: dict = {}
    greeting: str = "How can I help?"
    enabled_tools: list[str] = ["classify_issue", "search_docs", "summarize_issue"]


class UpdateWidgetRequest(BaseModel):
    allowed_origins: list[str] | None = None
    theme: dict | None = None
    greeting: str | None = None
    enabled_tools: list[str] | None = None


class SnippetResponse(BaseModel):
    widget_id: str
    snippet: str


@router.post("/widgets", response_model=WidgetConfig, status_code=201)
async def create_widget(
    body: CreateWidgetRequest,
    admin: User = Depends(require_admin),
) -> WidgetConfig:
    from app.services.widget_service import create_widget as svc_create
    return await svc_create(
        actor=admin,
        allowed_origins=body.allowed_origins,
        theme=body.theme,
        greeting=body.greeting,
        enabled_tools=body.enabled_tools,
    )


@router.put("/widgets/{widget_id}", response_model=WidgetConfig)
async def update_widget(
    widget_id: str,
    body: UpdateWidgetRequest,
    admin: User = Depends(require_admin),
) -> WidgetConfig:
    from app.services.widget_service import update_widget as svc_update
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    return await svc_update(actor=admin, widget_id=widget_id, **updates)


@router.get("/widgets", response_model=list[WidgetConfig])
async def list_widgets(
    _admin: User = Depends(require_admin),
) -> list[WidgetConfig]:
    from app.services.widget_service import list_widgets as svc_list
    return await svc_list()


@router.get("/widgets/{widget_id}/snippet", response_model=SnippetResponse)
async def get_snippet(
    widget_id: str,
    request: Request,
    _admin: User = Depends(require_admin),
) -> SnippetResponse:
    from app.services.widget_service import embed_snippet
    base = str(request.base_url).rstrip("/")
    return SnippetResponse(widget_id=widget_id, snippet=embed_snippet(widget_id, base))
