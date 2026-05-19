"""Streamlit entrypoint: login gate + navigation.

Authenticates against the api (JWT), then routes to chat / admin widget config
(admin only) / memory inspector pages. Internal tool — optimized for fast
iteration, not production polish.
"""

# TODO: login form -> store JWT in session; page nav by role
