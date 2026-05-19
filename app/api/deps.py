"""FastAPI dependencies — wiring only.

Provides the current authenticated user, role guards (user/admin), and service
instances to routers. Dependencies resolve services; routers never construct
repositories or infra adapters directly.
"""

# TODO: get_current_user, require_admin, service provider deps
