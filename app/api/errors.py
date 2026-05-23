"""The SINGLE exception handler mapping domain errors → HTTP responses.

Users never see a stack trace — they get a structured error body with a stable
code and a request ID. Domain exceptions map to status codes here. Every
uncaught exception is logged with the trace ID.
"""

from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    DomainError,
    NotFoundError,
    PermissionDenied,
    ToolFailure,
    ValidationError,
)

_STATUS_MAP: dict[type[DomainError], int] = {
    NotFoundError: 404,
    PermissionDenied: 403,
    ValidationError: 422,
    ToolFailure: 502,
}


def domain_error_to_response(exc: DomainError) -> JSONResponse:
    """Map a DomainError subclass to the appropriate HTTP status and JSON body."""
    status = _STATUS_MAP.get(type(exc), 400)
    return JSONResponse(
        status_code=status,
        content={"error": type(exc).__name__, "detail": str(exc)},
    )
