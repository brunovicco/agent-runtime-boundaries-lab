"""Small architecture test that protects framework boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTECTED = [
    ROOT / "src/agent_runtime_boundaries/domain",
    ROOT / "src/agent_runtime_boundaries/application",
]
FORBIDDEN = ("agno", "crewai", "langgraph", "a2a", "fastapi", "uvicorn")


def imports_in(path: Path) -> set[str]:
    """Return top-level import names from one Python file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".", 1)[0])
    return names


def main() -> None:
    """Fail if a protected layer imports a runtime framework."""
    violations: list[str] = []
    for folder in PROTECTED:
        for path in folder.rglob("*.py"):
            found = imports_in(path)
            bad = sorted(name for name in found if name.startswith(FORBIDDEN))
            if bad:
                violations.append(f"{path.relative_to(ROOT)} -> {', '.join(bad)}")
    if violations:
        raise SystemExit("architecture violations:\n" + "\n".join(violations))
    print("architecture boundaries: OK")


if __name__ == "__main__":
    main()
