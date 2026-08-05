from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src" / "kis_mcp"


def _python_sources(root: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)
    )


def _relative(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def _imported_modules(path: Path) -> frozenset[str]:
    relative = path.relative_to(SOURCE_ROOT)
    package = ("kis_mcp", *relative.parent.parts)
    imports: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:
            retained = len(package) - (node.level - 1)
            base_parts = package[: max(retained, 0)]
        else:
            base_parts = ()
        module_parts = tuple(node.module.split(".")) if node.module else ()
        base = ".".join((*base_parts, *module_parts))
        if base:
            imports.add(base)
        for alias in node.names:
            if alias.name == "*":
                continue
            imports.add(".".join(part for part in (base, alias.name) if part))
    return frozenset(imports)


def _imports_prefix(path: Path, prefix: str) -> bool:
    return any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in _imported_modules(path)
    )


def test_infrastructure_settings_do_not_depend_on_code_review_workflow() -> None:
    targets = (
        *_python_sources(SOURCE_ROOT / "providers" / "nvidia"),
        *_python_sources(SOURCE_ROOT / "tools" / "codex_cli"),
        SOURCE_ROOT / "providers" / "platform.py",
    )
    offenders = [
        _relative(path)
        for path in targets
        if _imports_prefix(path, "kis_mcp.workflows.code_review")
    ]

    assert offenders == []


def test_control_center_snapshot_delegates_storage_interpretation() -> None:
    source = (SOURCE_ROOT / "control_center" / "snapshot.py").read_text(
        encoding="utf-8"
    )
    forbidden = (
        "json.loads",
        "metadata.json",
        "subprocess.run",
        "runtime_settings_path",
        "policy_path",
        "provider_settings_path",
        "quarantine_root",
    )

    assert [fragment for fragment in forbidden if fragment in source] == []


def test_provider_smoke_modules_do_not_import_application_server() -> None:
    targets = (
        SOURCE_ROOT / "providers" / "github" / "smoke.py",
        SOURCE_ROOT / "providers" / "supabase" / "smoke.py",
    )
    offenders = [
        _relative(path)
        for path in targets
        if _imports_prefix(path, "kis_mcp.server")
    ]

    assert offenders == []


def test_root_provider_registry_alias_is_retired() -> None:
    alias = SOURCE_ROOT / "provider_registry.py"
    offenders = [
        _relative(path)
        for path in _python_sources(SOURCE_ROOT)
        if path != alias and _imports_prefix(path, "kis_mcp.provider_registry")
    ]

    assert alias.exists() is False
    assert offenders == []
