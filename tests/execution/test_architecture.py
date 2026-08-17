from __future__ import annotations

import ast
from pathlib import Path

import kis_mcp.execution as execution


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXECUTION_ROOT = REPOSITORY_ROOT / "src" / "kis_mcp" / "execution"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_execution_foundation_does_not_depend_on_workflow_layer() -> None:
    offenders = [
        path.name
        for path in EXECUTION_ROOT.glob("*.py")
        if any("workflows" in module for module in _imports(path))
    ]
    assert offenders == []


def test_hyperv_proof_uses_exact_archive_transfer_not_host_checkout_mount() -> None:
    source = (EXECUTION_ROOT / "hyperv.py").read_text(encoding="utf-8")
    assert "git -C $project archive" in source
    assert "Copy-VMFile" in source
    assert "New-VMSwitch" not in source
    assert "New-SmbShare" not in source


def test_virtualbox_disposable_provider_module_is_present() -> None:
    assert (EXECUTION_ROOT / "virtualbox.py").is_file()


def test_virtualbox_provider_is_exported_from_execution_package() -> None:
    assert hasattr(execution, "VirtualBoxDisposableExecutionProvider")
