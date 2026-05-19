"""Widget config business logic.

Admin-only create/edit of widget configs; changes write an audit-log row.
Generates the embed snippet shown in the Streamlit admin page. The
allowed_origins it manages drive the CORS allowlist and the embed route's CSP
frame-ancestors — origin allowlisting is enforced from the DB, not env.
"""

# TODO: create/update (-> audit), get_public_config, embed_snippet(widget_id)
