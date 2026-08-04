from __future__ import annotations

import ast
from pathlib import Path


PACKAGE = Path("src/kis_mcp/providers/github")


def test_github_provider_does_not_import_discover_or_work_enforcement() -> None:
    forbidden = {
        "kis_mcp.discover",
        "kis_mcp.desktop_commander",
        "kis_mcp.middleware",
        "kis_mcp.policy",
        "kis_mcp.quarantine",
        "kis_mcp.remote_runtime",
    }

    violations: list[str] = []
    for path in sorted(PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if any(name == item or name.startswith(f"{item}.") for item in forbidden):
                    violations.append(f"{path}:{name}")

    assert violations == []
