"""The SINGLE exception handler mapping domain errors -> HTTP responses.

Per the brief: users never see a stack trace; they see a structured error with
a stable code and a request ID. Domain exceptions map to status codes here
(NotFoundError->404, PermissionDenied->403, ValidationError->422,
ToolFailure->502, etc.). Every uncaught exception is logged with the trace ID
and the request ID.
"""

# TODO: install_exception_handlers(app): map DomainError subclasses + fallback
