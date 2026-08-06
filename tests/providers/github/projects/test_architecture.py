from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = (
    Path(__file__).resolve().parents[4]
    / "src"
    / "kis_mcp"
    / "providers"
    / "github"
    / "projects"
)


def test_github_project_adapter_contains_only_verified_read_tool_names() -> None:
    strings: set[str] = set()
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        strings.update(
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.startswith("projects_")
        )

    assert strings == {"projects_get", "projects_list"}


def test_adapter_does_not_import_gateway_workflows_or_fastmcp() -> None:
    forbidden = ("fastmcp", "kis_mcp.gateway", "kis_mcp.workflows")
    imports: set[str] = set()
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imports.add(node.module)

    assert not {name for name in imports if name.startswith(forbidden)}
