"""Domain exception hierarchy — distinct from infrastructure exceptions.

Per the brief: these are mapped to HTTP responses at the API boundary via a
SINGLE exception handler (app/api/errors.py). Users never see a stack trace —
they see a structured error with a code and a request ID.

Services raise these; repositories and infra raise their own technical errors
which services translate into these where appropriate.
"""


class DomainError(Exception):
    """Base for all domain errors. Carries a stable error `code`."""

    code = "domain_error"


class NotFoundError(DomainError):
    code = "not_found"


class PermissionDenied(DomainError):
    code = "permission_denied"


class ToolFailure(DomainError):
    """A chatbot tool (classifier/NER/summarizer/RAG) failed. Caught by the
    chat service so the bot degrades gracefully instead of 500-ing."""

    code = "tool_failure"


class ValidationError(DomainError):
    code = "validation_error"
