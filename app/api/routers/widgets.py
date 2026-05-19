"""Widget config routes (admin-only CRUD).

Admins create/edit widget configs and fetch the generated embed snippet.
Delegates to widget_service. Public read of a config (for the widget runtime)
is a separate, unauthenticated path — see embed.py.
"""

# TODO: POST/PUT/GET /widgets (require_admin), GET /widgets/{id}/snippet
