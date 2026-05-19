"""Auth routes: registration + login (fastapi-users, JWT).

Email/password registration. Delegates to auth_service. JWT signing key is
Vault-resolved at startup (never read here).
"""

# TODO: register, login, me — wired to fastapi-users + auth_service
