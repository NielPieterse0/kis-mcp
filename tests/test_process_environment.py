from __future__ import annotations

import asyncio
import os
from pathlib import Path
import shutil
import subprocess
import venv
from typing import Any

import pytest
from fastmcp import Client, FastMCP

from kis_mcp.desktop_commander import DesktopCommanderEffectResolver
from kis_mcp.middleware import ThreeRuleMiddleware
from kis_mcp.policy import ThreeRulePolicy
from kis_mcp.process_environment import (
    ProcessSourceIsolationError,
    RepositoryProcessEnvironmentNormalizer,
)
from kis_mcp.projects.contracts import ProjectDefinition
from kis_mcp.projects.registry import ProjectRegistry


def _registered_repo(tmp_path: Path) -> tuple[Path, ProjectRegistry]:
    root = tmp_path / "project"
    root.mkdir()
    (root / ".git").mkdir()
    (root / "src").mkdir()
    registry = ProjectRegistry(
        default_project_id="fixture",
        projects=(
            ProjectDefinition(
                project_id="fixture",
                display_name="Fixture",
                local_root=str(root),
            ),
        ),
    )
    return root, registry


def _worktree(root: Path, name: str) -> Path:
    worktree = root / ".work" / "worktrees" / name
    worktree.mkdir(parents=True)
    (worktree / ".git").write_text("gitdir: fixture\n", encoding="utf-8")
    (worktree / "src").mkdir()
    return worktree


def _normalizer(tmp_path: Path, registry: ProjectRegistry) -> RepositoryProcessEnvironmentNormalizer:
    return RepositoryProcessEnvironmentNormalizer(
        project_boundary=tmp_path,
        projects=registry,
    )


def test_default_process_shell_is_materialized_when_source_binding_is_added(tmp_path: Path) -> None:
    root, registry = _registered_repo(tmp_path)
    worktree = _worktree(root, "feature")
    command = f"Set-Location -LiteralPath '{worktree}'; python -c 'print(1)'"

    normalized = _normalizer(tmp_path, registry).normalize(
        "start_process",
        {"command": command, "timeout_ms": 1_000},
    )

    assert normalized["shell"] == "powershell.exe"
    assert "$kisProcessSource" in normalized["command"]

def test_powershell_process_binds_nearest_worktree_source(tmp_path: Path) -> None:
    root, registry = _registered_repo(tmp_path)
    worktree = _worktree(root, "feature")
    command = f"Set-Location -LiteralPath '{worktree}'; python -c 'print(1)'"

    normalized = _normalizer(tmp_path, registry).normalize(
        "start_process",
        {"command": command, "timeout_ms": 1_000, "shell": "powershell.exe"},
    )

    assert str(worktree / "src") in normalized["command"]
    assert str(root / "src") not in normalized["command"]
    assert "$env:PYTHONPATH" in normalized["command"]
    assert normalized["command"].endswith(command)


def test_cmd_process_binds_registered_worktree_source(tmp_path: Path) -> None:
    root, registry = _registered_repo(tmp_path)
    worktree = _worktree(root, "feature")
    command = f'cd /d "{worktree}" && python -c "print(1)"'

    normalized = _normalizer(tmp_path, registry).normalize(
        "start_process",
        {"command": command, "timeout_ms": 1_000, "shell": "cmd.exe"},
    )

    assert 'pushd "' in normalized["command"]
    assert 'set "PYTHONPATH=' in normalized["command"]
    assert str(worktree / "src") in normalized["command"]
    assert normalized["command"].endswith(command)


@pytest.mark.skipif(os.name != "nt", reason="cmd.exe regression")
def test_cmd_process_runs_when_selected_source_exists(tmp_path: Path) -> None:
    root, registry = _registered_repo(tmp_path)
    worktree = _worktree(root, "feature")
    command = f'cd /d "{worktree}" && echo SOURCE_BOUND'
    normalized = _normalizer(tmp_path, registry).normalize(
        "start_process",
        {"command": command, "timeout_ms": 1_000, "shell": "cmd.exe"},
    )

    completed = subprocess.run(
        normalized["command"],
        check=False,
        capture_output=True,
        text=True,
        shell=True,
        executable=os.environ.get("COMSPEC", "cmd.exe"),
    )

    assert completed.returncode == 0, completed.stderr
    assert "SOURCE_BOUND" in completed.stdout

@pytest.mark.skipif(os.name != "nt", reason="cmd.exe regression")
def test_cmd_process_fails_if_selected_source_disappears_before_execution(tmp_path: Path) -> None:
    root, registry = _registered_repo(tmp_path)
    worktree = _worktree(root, "feature")
    command = f'cd /d "{worktree}" && python -c "print(1)"'
    normalized = _normalizer(tmp_path, registry).normalize(
        "start_process",
        {"command": command, "timeout_ms": 1_000, "shell": "cmd.exe"},
    )
    shutil.rmtree(worktree / "src")

    completed = subprocess.run(
        normalized["command"],
        check=False,
        capture_output=True,
        text=True,
        shell=True,
        executable=os.environ.get("COMSPEC", "cmd.exe"),
    )

    assert completed.returncode != 0
    assert "PROCESS_SOURCE_UNAVAILABLE" in completed.stderr


def test_non_registered_or_non_source_process_is_unchanged(tmp_path: Path) -> None:
    _root, registry = _registered_repo(tmp_path)
    arguments = {
        "command": "Write-Output 'outside'",
        "timeout_ms": 1_000,
        "shell": "powershell.exe",
    }

    normalized = _normalizer(tmp_path, registry).normalize("start_process", arguments)

    assert normalized == arguments


@pytest.mark.parametrize(
    "override",
    [
        "$env:PYTHONPATH = 'C:\\wrong'",
        "Set-Item -Path Env:PYTHONPATH -Value 'C:\\wrong'",
        "Set-Item -Path Env:\\PYTHONPATH -Value 'C:\\wrong'",
        "Set-Item -Path Env:\\\\PYTHONPATH -Value 'C:\\wrong'",
        "Set-Item -Path Env:/PYTHONPATH -Value 'C:\\wrong'",
        "Set-Item -Path Env:/\\PYTHONPATH -Value 'C:\\wrong'",
        "Set-Item Env:\\PYTHONPATH -Value 'C:\\wrong'",
        "Set-Item -Value 'C:\\wrong' Env:\\PYTHONPATH",
        "Set-Item -Force Env:/PYTHONPATH -Value 'C:\\wrong'",
        "New-Item -Path Env:PYTHONPATH -Value 'C:\\wrong' -Force",
        "New-Item -Path Env:\\PYTHONPATH -Value 'C:\\wrong' -Force",
        "New-Item -Path Env:/PYTHONPATH -Value 'C:\\wrong' -Force",
        "[Environment]::SetEnvironmentVariable('PYTHONPATH', 'C:\\wrong', 'Process')",
    ],
)
def test_explicit_pythonpath_override_fails_closed(tmp_path: Path, override: str) -> None:
    root, registry = _registered_repo(tmp_path)
    worktree = _worktree(root, "feature")
    command = f"Set-Location -LiteralPath '{worktree}'; {override}; python -c 'print(1)'"

    with pytest.raises(ProcessSourceIsolationError) as exc_info:
        _normalizer(tmp_path, registry).normalize(
            "start_process",
            {"command": command, "timeout_ms": 1_000, "shell": "powershell.exe"},
        )

    assert exc_info.value.code == "PROCESS_SOURCE_OVERRIDE_UNSAFE"


@pytest.mark.parametrize(
    "benign_command",
    [
        "Set-Content -Path output.txt -Value 'Env:\\PYTHONPATH'",
        "Set-Item -Path Env:KIS_265_BIND 'Env:PYTHONPATH'",
        "Set-Item -Path Env:KIS_265_BIND 'Env:\\PYTHONPATH'",
        "Set-Item -Path Env:KIS_265_BIND 'Env:\\\\PYTHONPATH'",
        "Set-Item -Path Env:KIS_265_BIND 'Env:/PYTHONPATH'",
        "Set-Content -Path output.txt 'Env:PYTHONPATH'",
        "Set-Content -Path output.txt 'Env:\\PYTHONPATH'",
        "Set-Content -Path output.txt 'Env:/PYTHONPATH'",
        "Set-Item -Path Env://PYTHONPATH -Value 'safe'",
        "Set-Item -Path Env:\\/PYTHONPATH -Value 'safe'",
        r"Set-Item -Path Env:\\\PYTHONPATH -Value 'safe'",
        r"Set-Item -Path Env:/\\PYTHONPATH -Value 'safe'",
    ],
)
def test_pythonpath_provider_text_used_only_as_data_is_not_rejected(
    tmp_path: Path,
    benign_command: str,
) -> None:
    root, registry = _registered_repo(tmp_path)
    worktree = _worktree(root, "feature")
    command = (
        f"Set-Location -LiteralPath '{worktree}'; "
        f"{benign_command}; python -c 'print(1)'"
    )

    normalized = _normalizer(tmp_path, registry).normalize(
        "start_process",
        {"command": command, "timeout_ms": 1_000, "shell": "powershell.exe"},
    )

    assert str(worktree / "src") in normalized["command"]
    assert normalized["command"].endswith(command)


def test_multiple_registered_worktree_sources_fail_closed(tmp_path: Path) -> None:
    root, registry = _registered_repo(tmp_path)
    first = _worktree(root, "one")
    second = _worktree(root, "two")
    command = (
        f"Set-Location -LiteralPath '{first}'; python -c 'print(1)'; "
        f"Set-Location -LiteralPath '{second}'; python -c 'print(2)'"
    )

    with pytest.raises(ProcessSourceIsolationError) as exc_info:
        _normalizer(tmp_path, registry).normalize(
            "start_process",
            {"command": command, "timeout_ms": 1_000, "shell": "powershell.exe"},
        )

    assert exc_info.value.code == "PROCESS_SOURCE_AMBIGUOUS"


def test_unsupported_shell_fails_when_source_binding_is_required(tmp_path: Path) -> None:
    root, registry = _registered_repo(tmp_path)
    worktree = _worktree(root, "feature")
    command = f"cd '{worktree}' && python -c 'print(1)'"

    with pytest.raises(ProcessSourceIsolationError) as exc_info:
        _normalizer(tmp_path, registry).normalize(
            "start_process",
            {"command": command, "timeout_ms": 1_000, "shell": "bash"},
        )

    assert exc_info.value.code == "PROCESS_SOURCE_SHELL_UNSUPPORTED"


def test_middleware_forwards_source_bound_command_to_policy_and_provider(tmp_path: Path) -> None:
    root, registry = _registered_repo(tmp_path)
    worktree = _worktree(root, "feature")
    command = f"Set-Location -LiteralPath '{worktree}'; python -c 'print(1)'"
    resolved: list[dict[str, Any]] = []
    executed: list[str] = []

    base_resolver = DesktopCommanderEffectResolver(
        project_boundary=str(tmp_path),
        provider_state_file=str(tmp_path / "provider.json"),
    )

    class _Resolver:
        @property
        def capabilities(self):
            return base_resolver.capabilities

        def resolve(self, tool_name: str, arguments: dict[str, Any]):
            resolved.append(dict(arguments))
            return base_resolver.resolve(tool_name, arguments)

    server = FastMCP("process-source-middleware-test")

    @server.tool
    def start_process(command: str, timeout_ms: int, shell: str | None = None) -> str:
        executed.append(command)
        return command

    server.add_middleware(
        ThreeRuleMiddleware(
            resolver=_Resolver(),
            policy=ThreeRulePolicy(
                project_boundary=str(tmp_path),
                quarantine_root=str(tmp_path / "quarantine"),
            ),
            quarantine_paths=lambda _paths: [],
            process_environment_normalizer=_normalizer(tmp_path, registry),
        )
    )

    async def run() -> None:
        async with Client(server) as client:
            await client.call_tool(
                "start_process",
                {"command": command, "timeout_ms": 1_000, "shell": "powershell.exe"},
            )

    asyncio.run(run())
    assert str(worktree / "src") in executed[0]
    assert resolved[0]["command"] == executed[0]


@pytest.mark.skipif(os.name != "nt" or shutil.which("pwsh") is None, reason="Windows PowerShell regression")
def test_shared_editable_path_metadata_cannot_override_selected_worktree(tmp_path: Path) -> None:
    root, registry = _registered_repo(tmp_path)
    worktree = _worktree(root, "feature")
    package = "kis_source_probe_265"
    root_package = root / "src" / package
    worktree_package = worktree / "src" / package
    root_package.mkdir()
    worktree_package.mkdir()
    (root_package / "__init__.py").write_text("SOURCE = 'root-main'\n", encoding="utf-8")
    (worktree_package / "__init__.py").write_text("SOURCE = 'worktree'\n", encoding="utf-8")

    environment = tmp_path / "shared-env"
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / "Scripts" / "python.exe"
    site_packages = Path(
        subprocess.run(
            [str(python), "-c", "import site; print(site.getsitepackages()[0])"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    (site_packages / "root-main-editable.pth").write_text(str(root / "src") + "\n", encoding="utf-8")

    command = (
        f"Set-Location -LiteralPath '{worktree}'; "
        f"& '{python}' -c \"import {package}; print({package}.SOURCE)\""
    )
    clean_environment = dict(os.environ)
    clean_environment.pop("PYTHONPATH", None)
    baseline = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
        env=clean_environment,
    )
    assert baseline.stdout.strip() == "root-main"

    normalized = _normalizer(tmp_path, registry).normalize(
        "start_process",
        {"command": command, "timeout_ms": 10_000, "shell": "powershell.exe"},
    )
    isolated = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", normalized["command"]],
        check=True,
        capture_output=True,
        text=True,
        env=clean_environment,
    )
    assert isolated.stdout.strip() == "worktree"
