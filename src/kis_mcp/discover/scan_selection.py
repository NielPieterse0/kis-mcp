from __future__ import annotations

from pathlib import PurePosixPath


_PROJECT_MARKERS = frozenset(
    {
        "agents.md",
        "cargo.toml",
        "claude.md",
        "composer.json",
        "gemfile",
        "gemini.md",
        "go.mod",
        "package-lock.json",
        "package.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "pom.xml",
        "pyproject.toml",
        "readme.md",
        "requirements.txt",
        "spec.md",
        "uv.lock",
        "yarn.lock",
    }
)
_SOURCE_ROOTS = frozenset(
    {
        "app",
        "apps",
        "backend",
        "client",
        "frontend",
        "lib",
        "libs",
        "packages",
        "server",
        "services",
        "src",
    }
)
_SUPPORT_ROOTS = frozenset(
    {
        ".github",
        "config",
        "configs",
        "contracts",
        "schema",
        "schemas",
        "test",
        "tests",
    }
)
_DOCUMENTATION_ROOTS = frozenset({"doc", "docs", "documentation"})
_AUXILIARY_ROOTS = frozenset(
    {
        ".agents",
        ".archive",
        "archive",
        "archives",
        "examples",
        "third_party",
        "vendor",
    }
)


def evidence_path_priority(label: str) -> tuple[int, str]:
    """Rank repository paths for deterministic high-value-first traversal."""
    path = PurePosixPath(label)
    parts = tuple(part.casefold() for part in path.parts)
    name = parts[-1]
    first = parts[0]

    if len(parts) == 1 and name in _PROJECT_MARKERS:
        tier = 0
    elif first in _SOURCE_ROOTS:
        tier = 1
    elif first in _SUPPORT_ROOTS:
        tier = 2
    elif first in _AUXILIARY_ROOTS or (first.startswith(".") and first != ".github"):
        tier = 5
    elif first in _DOCUMENTATION_ROOTS or name.endswith(".md"):
        tier = 3
    else:
        tier = 4
    return tier, label.casefold()


__all__ = ["evidence_path_priority"]
