from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src" / "kis_mcp"


def _python_sources(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts))


def _relative(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def test_infrastructure_settings_do_not_depend_on_code_review_workflow() -> None:
    targets = (
        *_python_sources(SOURCE_ROOT / "providers" / "nvidia"),
        *_python_sources(SOURCE_ROOT / "tools" / "codex_cli"),
        SOURCE_ROOT / "providers" / "platform.py",
    )
    offenders = [
        _relative(path)
        for path in targets
        if "workflows.code_review" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_control_center_snapshot_delegates_storage_interpretation() -> None:
    source = (SOURCE_ROOT / "control_center" / "snapshot.py").read_text(encoding="utf-8")
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


def test_provider_packages_do_not_import_application_server() -> None:
    offenders = [
        _relative(path)
        for path in _python_sources(SOURCE_ROOT / "providers")
        if "kis_mcp.server" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_root_provider_registry_alias_is_retired() -> None:
    alias = SOURCE_ROOT / "provider_registry.py"
    imports = (
        "kis_mcp.provider_registry",
        "from kis_mcp import provider_registry",
    )
    offenders = [
        _relative(path)
        for path in _python_sources(SOURCE_ROOT)
        if path != alias
        and any(fragment in path.read_text(encoding="utf-8") for fragment in imports)
    ]

    assert alias.exists() is False
    assert offenders == []
