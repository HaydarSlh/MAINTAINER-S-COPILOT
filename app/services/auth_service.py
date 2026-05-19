"""Auth + authorization business logic.

fastapi-users with JWT, email/password registration. JWT signing key resolves
from Vault at startup. Two roles: user and admin. Admin-only actions (invite
users, configure widgets) are authorized here; role changes write an audit row.
"""

# TODO: register, authenticate, require_admin, change_role (-> audit_repo)
