"""Widget config persistence. SQL only.

The `widget` table is keyed by public widget_id with allowed_origins, theme,
greeting, enabled_tools. Read on the embed path to drive CORS + CSP
frame-ancestors; written by admins via the Streamlit config page.
"""

# TODO: get_by_widget_id, create, update, list
