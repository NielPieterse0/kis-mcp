from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DISCOVER_ROOT = REPOSITORY_ROOT / "src" / "kis_mcp" / "discover"

FORBIDDEN_IMPORTS = {
    "aiohttp",
    "httpx",
    "requests",
    "socket",
    "sdk_tool",
    "dev_intel",
    "dev_intel_tool",
    "mcp_tool",
    "kis_mcp.desktop_commander",
    "kis_mcp.middleware",
    "kis_mcp.policy",
    "kis_mcp.quarantine",
    "kis_mcp.quarantine_integrity",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _qualified_call(node: ast.Call) -> str | None:
    parts: list[str] = []
    value = node.func
    while isinstance(value, ast.Attribute):
        parts.append(value.attr)
        value = value.value
    if isinstance(value, ast.Name):
        parts.append(value.id)
        return ".".join(reversed(parts))
    return None


def test_discover_has_no_work_network_or_donor_dependencies() -> None:
    violations: list[str] = []
    for path in sorted(DISCOVER_ROOT.glob("*.py")):
        for imported in _imports(path):
            if any(
                imported == forbidden or imported.startswith(f"{forbidden}.")
                for forbidden in FORBIDDEN_IMPORTS
            ):
                violations.append(f"{path.name}: {imported}")
    assert violations == []


def test_fastmcp_and_subprocess_are_confined_to_approved_adapters() -> None:
    violations: list[str] = []
    for path in sorted(DISCOVER_ROOT.glob("*.py")):
        imported = _imports(path)
        if any(name == "fastmcp" or name.startswith("fastmcp.") for name in imported):
            if path.name not in {"tools.py", "platform.py"}:
                violations.append(f"FastMCP import in {path.name}")
        if any(name == "subprocess" or name.startswith("subprocess.") for name in imported):
            if path.name != "git_reader.py":
                violations.append(f"subprocess import in {path.name}")
    assert violations == []


def test_filesystem_traversal_is_confined_to_read_boundary_modules() -> None:
    allowed = {"read_authority.py", "scanner.py"}
    traversal_calls = {
        "os.scandir",
        "os.walk",
        "Path.glob",
        "Path.rglob",
        "Path.iterdir",
    }
    violations: list[str] = []
    for path in sorted(DISCOVER_ROOT.glob("*.py")):
        if path.name in allowed:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            call = _qualified_call(node)
            if call in traversal_calls or call in {"glob", "rglob", "iterdir"}:
                violations.append(f"{path.name}:{node.lineno}: {call}")
    assert violations == []
