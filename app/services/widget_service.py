"""Widget config business logic — admin-only, every change is audited.

allowed_origins drives CORS + CSP frame-ancestors; enforced from DB, not env.
"""

from __future__ import annotations

from app.domain.models import User, WidgetConfig

_VALID_TOOLS = {"classify_issue", "extract_entities", "search_docs",
                "summarize_issue", "write_memory"}


def _validate_origins(origins: list[str]) -> None:
    """Raise ValidationError if any origin does not start with http:// or https://."""
    for o in origins:
        if not (o.startswith("http://") or o.startswith("https://")):
            from app.domain.exceptions import ValidationError
            raise ValidationError(
                f"Origin {o!r} must start with http:// or https://"
            )


def _validate_tools(tools: list[str]) -> None:
    """Raise ValidationError if any tool name is not in the allowed set."""
    unknown = set(tools) - _VALID_TOOLS
    if unknown:
        from app.domain.exceptions import ValidationError
        raise ValidationError(f"Unknown tools: {unknown}")


async def create_widget(
    actor: User,
    allowed_origins: list[str],
    theme: dict,
    greeting: str,
    enabled_tools: list[str],
) -> WidgetConfig:
    """Validate, persist, and audit-log a new widget config."""
    _validate_origins(allowed_origins)
    _validate_tools(enabled_tools)

    from app.db.session import get_session
    from app.repositories import audit_repo, widget_repo

    async with get_session() as session:
        async with session.begin():
            config = await widget_repo.create(
                session,
                owner_id=actor.id,
                allowed_origins=allowed_origins,
                theme=theme,
                greeting=greeting,
                enabled_tools=enabled_tools,
            )
            await audit_repo.append(
                session,
                actor_id=actor.id,
                action="widget.create",
                target_type="widget",
                target_id=config.widget_id,
                detail={"allowed_origins": allowed_origins, "enabled_tools": enabled_tools},
            )
    return config


async def update_widget(
    actor: User,
    widget_id: str,
    **kwargs,
) -> WidgetConfig:
    """Apply validated updates to a widget config and write an audit-log row."""
    if "allowed_origins" in kwargs:
        _validate_origins(kwargs["allowed_origins"])
    if "enabled_tools" in kwargs:
        _validate_tools(kwargs["enabled_tools"])

    from app.db.session import get_session
    from app.domain.exceptions import NotFoundError
    from app.repositories import audit_repo, widget_repo

    async with get_session() as session:
        async with session.begin():
            try:
                config = await widget_repo.update(session, widget_id=widget_id, **kwargs)
            except ValueError as exc:
                raise NotFoundError(str(exc)) from exc
            await audit_repo.append(
                session,
                actor_id=actor.id,
                action="widget.update",
                target_type="widget",
                target_id=widget_id,
                detail={"fields": list(kwargs.keys())},
            )
    return config


async def get_public_config(widget_id: str) -> WidgetConfig | None:
    """Return the public config for an active widget, or None if not found."""
    from app.db.session import get_session
    from app.repositories import widget_repo

    async with get_session() as session:
        return await widget_repo.get_by_widget_id(session, widget_id)


async def list_widgets() -> list[WidgetConfig]:
    """Return all active widget configurations."""
    from app.db.session import get_session
    from app.repositories import widget_repo

    async with get_session() as session:
        return await widget_repo.list_all(session)


def embed_snippet(widget_id: str, api_base_url: str) -> str:
    """Return the one-line <script> tag an admin pastes into their site."""
    return (
        f'<script src="{api_base_url}/widget.js" '
        f'data-widget-id="{widget_id}" async></script>'
    )
