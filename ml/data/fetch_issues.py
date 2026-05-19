"""Fetch CLOSED issues from the chosen open-source repo (locked Monday).

Pulls issue title/body/labels/timestamps via the GitHub API. Output is
reproducible (script-driven), not committed. A held-out slice of resolved
issues with maintainer answers is reserved for the RAG corpus and must NOT
appear in classifier training (data-leakage discipline).
"""

# TODO: fetch(repo) -> raw issues; persist to ml/data/raw/
