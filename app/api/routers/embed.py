"""Embed route + public widget config — the production origin-allowlisting path.

Per the brief:
  - serves the loader script at /widget.js (host pastes one <script> tag with
    data-widget-id; the loader injects the iframe pointing at the React bundle),
  - serves the widget's public config (theme, greeting, enabled tools) by
    widget_id at load time,
  - sets a Content-Security-Policy header with frame-ancestors matching the
    widget's allowed_origins so unallowed parents cannot iframe the widget,
  - CORS allowlist is enforced from the DB allowed_origins, NOT a hardcoded env.

Friday demo: widget loads on an allowed host, blocked on a non-allowlisted one.
"""

# TODO: GET /widget.js (loader), GET /embed/config/{widget_id} (+ CSP header)
