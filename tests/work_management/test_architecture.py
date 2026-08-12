from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "src" / "kis_mcp" / "work_management"
FORBIDDEN_IMPORT_PREFIXES = (
    "fastmcp",
    "kis_mcp.capabilities",
    "kis_mcp.gateway",
    "kis_mcp.providers",
    "kis_mcp.workflows",
)


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module)
    return modules


def test_work_management_package_has_bounded_files_and_no_platform_dependencies() -> None:
    files = {path.name for path in PACKAGE.glob("*.py")}
    assert files == {
        "__init__.py",
        "backend.py",
        "contracts.py",
        "evidence.py",
        "intake.py",
        "lifecycle.py",
        "records.py",
        "reconciliation.py",
        "reviews.py",
        "schema.py",
        "selection.py",
        "service.py",
        "settings.py",
        "status.py",
        "traceability.py",
    }

    imports = {
        module
        for path in PACKAGE.glob("*.py")
        for module in imported_modules(path)
    }
    assert not {
        module
        for module in imports
        if module.startswith(FORBIDDEN_IMPORT_PREFIXES)
    }
