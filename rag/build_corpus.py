"""Assemble the RAG corpus and run the preprocessing pipeline.

Corpus = pydantic/pydantic docs/ markdown files  +  held-out resolved Q&A issues.
The held-out issues are closed question/bug issues with ≥2 comments and at least
one maintainer reply — excluded from classifier training to avoid data leakage
(DECISIONS.md D1).

Run as an offline job before indexing:
    python -m rag.build_corpus
Outputs a list of Document dicts to stdout (JSON) or saves to disk when --out is given.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

# ── Document schema ───────────────────────────────────────────────────────────

@dataclass
class Document:
    doc_id: str          # unique stable identifier
    content: str         # cleaned text
    source: str          # "docs" | "issue"
    metadata: dict       # path/url, title, labels, date, issue_number, etc.


# ── GitHub helpers ─────────────────────────────────────────────────────────────

def _github_token() -> str:
    try:
        from app.infra.vault import read_secret
        token = read_secret("secret/data/llm").get("github_token", "")
        if token:
            return token
    except Exception:
        pass
    return os.environ.get("GITHUB_TOKEN", "")


def _gh_get(url: str, token: str) -> dict | list:
    """Simple GitHub API GET with rate-limit backoff. Raises on 404 immediately."""
    import urllib.error
    import urllib.request
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    delay = 5
    for attempt in range(6):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise   # not found — don't retry
            if e.code in (403, 429):
                print(f"  Rate limited (HTTP {e.code}), retry in {delay}s ...", file=sys.stderr)
                time.sleep(delay)
                delay = min(delay * 2, 120)
            else:
                raise
        except Exception as e:
            msg = str(e)
            if "secondary rate" in msg.lower():
                print(f"  Rate limited, retry in {delay}s ...", file=sys.stderr)
                time.sleep(delay)
                delay = min(delay * 2, 120)
            else:
                raise
    raise RuntimeError(f"GitHub API failed after retries: {url}")


# ── Docs fetcher ───────────────────────────────────────────────────────────────

_DOCS_SUBDIRS = ["", "concepts", "api", "integrations", "errors", "examples"]
_REPO = "pydantic/pydantic"
_BRANCH = "main"


def _fetch_docs_tree(token: str) -> list[dict]:
    """Fetch the recursive file tree of docs/ from the GitHub API."""
    url = f"https://api.github.com/repos/{_REPO}/git/trees/{_BRANCH}?recursive=1"
    tree = _gh_get(url, token)
    return [
        item for item in tree.get("tree", [])
        if item.get("type") == "blob"
        and item["path"].startswith("docs/")
        and item["path"].endswith(".md")
    ]


def _fetch_raw(path: str, token: str) -> str:
    import urllib.request
    url = f"https://raw.githubusercontent.com/{_REPO}/{_BRANCH}/{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _clean_markdown(text: str) -> str:
    """Strip MkDocs-specific syntax, keep semantic content."""
    # Remove frontmatter
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    # Remove admonition markers (!!!, ???) but keep content
    text = re.sub(r"^[!?]{3}.*?\n", "", text, flags=re.MULTILINE)
    # Remove Material tab markers (=== "Tab name")
    text = re.sub(r'^===\s+"[^"]*"\n', "", text, flags=re.MULTILINE)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_docs(token: str = "") -> Iterator[Document]:
    """Yield Document for each markdown file under docs/ in pydantic/pydantic."""
    print("Fetching pydantic docs tree ...", file=sys.stderr)
    tree = _fetch_docs_tree(token)
    print(f"  Found {len(tree)} markdown files", file=sys.stderr)

    for item in tree:
        path = item["path"]
        try:
            raw = _fetch_raw(path, token)
            content = _clean_markdown(raw)
            if len(content) < 50:   # skip empty/tiny files
                continue
            title = Path(path).stem.replace("-", " ").replace("_", " ").title()
            yield Document(
                doc_id=f"docs::{path}",
                content=content,
                source="docs",
                metadata={"path": path, "title": title, "repo": _REPO},
            )
        except Exception as e:
            print(f"  WARNING: could not fetch {path}: {e}", file=sys.stderr)


# ── Held-out issues fetcher ────────────────────────────────────────────────────

# Known pydantic core maintainers — no API call needed, checked locally only.
# Covers all active maintainers as of 2026. Add names here if issues are missed.
_KNOWN_MAINTAINERS = {
    "samuelcolvin", "PrettyWood", "dmontagu", "hramezani",
    "adriangb", "sydney-runkle", "Kludex", "davidhewitt",
    "MarkusSintonen", "dzmitry-lahoda", "nrbnlulu", "Viicos",
    "recogna-nlp", "tobiasraabe", "jonaslagoni", "pydantic-bot",
}


def _has_maintainer_reply(comments: list[dict], token: str) -> bool:
    """Return True if any comment author is a known pydantic maintainer."""
    for c in comments:
        user = (c.get("user") or {}).get("login", "")
        if user in _KNOWN_MAINTAINERS:
            return True
    return False


def fetch_issues(token: str = "", max_issues: int = 400) -> Iterator[Document]:
    """Yield Document for each held-out resolved Q&A issue.

    Filters: closed, labels question OR bug, ≥2 comments, at least one
    maintainer reply. These rows are excluded from classifier training.
    """
    print("Fetching held-out resolved issues ...", file=sys.stderr)
    fetched = 0
    page = 1

    while fetched < max_issues:
        url = (
            f"https://api.github.com/repos/{_REPO}/issues"
            f"?state=closed&labels=question&per_page=100&page={page}"
            f"&sort=created&direction=desc"
        )
        issues = _gh_get(url, token)
        if not isinstance(issues, list) or not issues:
            break

        for issue in issues:
            if fetched >= max_issues:
                break
            if issue.get("pull_request"):
                continue   # skip PRs
            if issue.get("comments", 0) < 2:
                continue

            number = issue["number"]
            comments_url = f"https://api.github.com/repos/{_REPO}/issues/{number}/comments"
            try:
                comments = _gh_get(comments_url, token)
            except Exception:
                continue

            if not isinstance(comments, list) or not _has_maintainer_reply(comments, None):
                continue

            # Build content: title + body + best maintainer reply
            body = (issue.get("body") or "").strip()
            maintainer_comments = [
                c["body"] for c in comments
                if (c.get("user") or {}).get("login", "") in _KNOWN_MAINTAINERS
                and c.get("body")
            ]
            best_reply = maintainer_comments[0] if maintainer_comments else ""
            content = f"# {issue['title']}\n\n{body}\n\n## Maintainer reply\n\n{best_reply}"
            content = re.sub(r"\n{3,}", "\n\n", content).strip()

            if len(content) < 100:
                continue

            labels = [l["name"] for l in issue.get("labels", [])]
            yield Document(
                doc_id=f"issue::{number}",
                content=content,
                source="issue",
                metadata={
                    "issue_number": number,
                    "title": issue["title"],
                    "labels": labels,
                    "created_at": issue.get("created_at", ""),
                    "url": issue.get("html_url", ""),
                },
            )
            fetched += 1
            if fetched % 50 == 0:
                print(f"  Fetched {fetched} issues ...", file=sys.stderr)

        page += 1

    print(f"  Total held-out issues: {fetched}", file=sys.stderr)


# ── Entry point ────────────────────────────────────────────────────────────────

def build(max_issues: int = 400) -> list[Document]:
    token = _github_token()
    docs = list(fetch_docs(token))
    issues = list(fetch_issues(token, max_issues=max_issues))
    corpus = docs + issues
    print(f"Corpus built: {len(docs)} doc files + {len(issues)} issues = {len(corpus)} total",
          file=sys.stderr)
    return corpus


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="corpus.jsonl")
    parser.add_argument("--max-issues", type=int, default=400)
    args = parser.parse_args()

    corpus = build(max_issues=args.max_issues)
    with open(args.out, "w", encoding="utf-8") as f:
        for doc in corpus:
            f.write(json.dumps(asdict(doc), ensure_ascii=False) + "\n")
    print(f"Saved {len(corpus)} documents → {args.out}")
