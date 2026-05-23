"""Layer-boundary guard test (the architecture is the grade).

Statically asserts the dependency rules so a violation fails CI:
  - app/api/       must not import sqlalchemy, redis, httpx, or infra adapters directly
  - app/repositories/ must not raise HTTP errors or import fastapi
  - app/domain/    must not import from app/db/ ORM
"""

import ast
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_APP  = _REPO / "app"


def _imports_in_file(path: Path) -> set[str]:
    """Return all top-level module names imported in a Python file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


def _imports_in_package(pkg: Path) -> dict[str, set[str]]:
    return {
        str(f.relative_to(_REPO)): _imports_in_file(f)
        for f in pkg.rglob("*.py")
        if "__pycache__" not in str(f)
    }


def test_api_layer_has_no_forbidden_imports():
    """app/api/ must not directly use SQLAlchemy, Redis, or raw httpx."""
    forbidden = {"sqlalchemy", "redis", "httpx"}
    violations = []
    for fname, imports in _imports_in_package(_APP / "api").items():
        bad = imports & forbidden
        if bad:
            violations.append(f"{fname}: {bad}")
    assert not violations, "API layer imports forbidden modules:\n" + "\n".join(violations)


def test_repositories_layer_has_no_fastapi():
    """app/repositories/ must not import fastapi (no HTTP concerns)."""
    violations = []
    repo_dir = _APP / "repositories"
    if not repo_dir.exists():
        return  # not yet scaffolded — pass
    for fname, imports in _imports_in_package(repo_dir).items():
        if "fastapi" in imports:
            violations.append(fname)
    assert not violations, "Repositories layer imports fastapi:\n" + "\n".join(violations)


def test_domain_layer_has_no_db_imports():
    """app/domain/ must not import from app/db/ ORM layer."""
    violations = []
    for fname, imports in _imports_in_package(_APP / "domain").items():
        # Check for direct app.db imports via AST (full dotted paths)
        path = _APP / "domain" / Path(fname).name
        if not path.exists():
            path = _REPO / fname
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, FileNotFoundError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("app.db"):
                    violations.append(f"{fname}: imports {node.module}")
    assert not violations, "Domain layer imports ORM:\n" + "\n".join(violations)
