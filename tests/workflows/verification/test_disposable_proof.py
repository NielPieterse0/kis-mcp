from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kis_mcp.execution.hyperv import HyperVDisposableExecutionProvider
from kis_mcp.execution.settings import (
    HyperVProfileSettings,
    RunnerProfileSettings,
    VirtualBoxProfileSettings,
)
from kis_mcp.execution.virtualbox import VirtualBoxDisposableExecutionProvider
from kis_mcp.workflows.verification.proof import DisposableVerificationProofService


@dataclass
class _Inspection:
    verification: dict[str, Any]


class _Inspector:
    def inspect(self, request: Any) -> _Inspection:
        return _Inspection(
            verification={
                "declarations": [
                    {
                        "id": "python-pytest",
                        "title": "Run Python pytest suite",
                        "category": "test",
                        "source_path": "tests/test_sample.py",
                        "profile": "python",
                        "arguments": ["-m", "pytest", "-q"],
                    }
                ]
            }
        )


class _Runner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, tool: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((tool, arguments))
        command = str(arguments.get("command", ""))
        if "Invoke-Command -VMName" in command:
            guest = json.dumps({"exit_code": 0, "stdout": "proof ok", "stderr": ""})
            return {"text": f"__KIS_GUEST_RESULT={guest}\n__KIS_EXECUTION_EXIT_CODE=0\n"}
        return {"text": "ok\n__KIS_EXECUTION_EXIT_CODE=0\n"}


def _profile(tmp_path: Path) -> RunnerProfileSettings:
    return RunnerProfileSettings(
        profile_id="windows-hyperv-proof",
        backend_id="windows-hyperv",
        enabled=False,
        image_id="windows-hyperv-proof-v1",
        toolchain_id="repository-declared-v1",
        hyperv=HyperVProfileSettings(
            template_vm="kis-windows-template",
            checkpoint_name="clean",
            state_root=str(tmp_path / "hyperv"),
            guest_workspace=r"C:\KIS\workspace",
            guest_username_env="KIS_HYPERV_GUEST_USERNAME",
            guest_password_env="KIS_HYPERV_GUEST_PASSWORD",
            startup_timeout_ms=60_000,
            cleanup_timeout_ms=30_000,
        ),
    )


def test_declared_verification_can_run_through_exact_hyperv_proof_path(tmp_path: Path) -> None:
    runner = _Runner()
    profile = _profile(tmp_path)
    provider = HyperVDisposableExecutionProvider.from_profile(runner, profile)
    service = DisposableVerificationProofService(
        inspector=_Inspector(),
        provider=provider,
        runner_profile=profile,
    )

    result = asyncio.run(
        service.run(
            project=r"C:\Projects\kis-mcp",
            exact_revision="9adf1ca26a6a96a173605a7e5dd5c11216d6ec0e",
            verification_id="python-pytest",
            timeout_ms=120_000,
        )
    )

    assert result.verification.status == "passed"
    assert result.verification.profile == "python"
    assert result.verification.evidence == "proof ok"
    assert result.execution.source_revision == "9adf1ca26a6a96a173605a7e5dd5c11216d6ec0e"
    assert result.execution.image_id == profile.image_id
    assert result.execution.toolchain_id == profile.toolchain_id
    commands = [str(arguments.get("command", "")) for _, arguments in runner.calls]
    assert any("git -C" in command for command in commands)
    assert any("Invoke-Command -VMName" in command for command in commands)


class _VirtualBoxRunner:
    def __init__(self, state_root: Path) -> None:
        self.state_root = state_root
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, tool: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((tool, arguments))
        command = str(arguments.get("command", ""))
        if "'snapshot'" in command and "'showvminfo'" in command:
            config = self.state_root / "vbox-home" / "Machines" / "template.vbox"
            return {
                "text": f"Config file:     {config}\n__KIS_EXECUTION_EXIT_CODE=0\n"
            }
        if "showvminfo" in command and "kis-windows-template" in command:
            config = self.state_root / "vbox-home" / "Machines" / "template.vbox"
            return {"text": f'CfgFile="{config}"\n__KIS_EXECUTION_EXIT_CODE=0\n'}
        if "guestcontrol" in command and "'run'" in command:
            guest = json.dumps({"exit_code": 0, "stdout": "proof ok", "stderr": ""})
            return {"text": f"__KIS_GUEST_RESULT={guest}\n__KIS_EXECUTION_EXIT_CODE=0\n"}
        return {"text": "ok\n__KIS_EXECUTION_EXIT_CODE=0\n"}


def _virtualbox_profile(tmp_path: Path) -> RunnerProfileSettings:
    state_root = tmp_path / "virtualbox"
    return RunnerProfileSettings(
        profile_id="windows-virtualbox-proof",
        backend_id="windows-virtualbox",
        enabled=False,
        image_id="windows-virtualbox-proof-v1",
        toolchain_id="repository-declared-v1",
        virtualbox=VirtualBoxProfileSettings(
            vboxmanage_path=r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
            template_vm="kis-windows-template",
            snapshot_name="clean",
            state_root=str(state_root),
            vbox_user_home=str(state_root / "vbox-home"),
            guest_workspace=r"C:\KIS\workspace",
            guest_username_env="KIS_VIRTUALBOX_GUEST_USERNAME",
            guest_password_file_env="KIS_VIRTUALBOX_GUEST_PASSWORD_FILE",
            startup_timeout_ms=60_000,
            cleanup_timeout_ms=30_000,
        ),
    )


def test_declared_verification_can_run_through_exact_virtualbox_proof_path(
    tmp_path: Path, monkeypatch: Any
) -> None:
    profile = _virtualbox_profile(tmp_path)
    assert profile.virtualbox is not None
    password_file = Path(profile.virtualbox.state_root) / "credentials" / "guest.txt"
    password_file.parent.mkdir(parents=True, exist_ok=True)
    password_file.write_text("proof-password", encoding="utf-8")
    monkeypatch.setenv(profile.virtualbox.guest_username_env, "kis-runner")
    monkeypatch.setenv(profile.virtualbox.guest_password_file_env, str(password_file))
    runner = _VirtualBoxRunner(Path(profile.virtualbox.state_root))
    provider = VirtualBoxDisposableExecutionProvider.from_profile(runner, profile)
    service = DisposableVerificationProofService(
        inspector=_Inspector(), provider=provider, runner_profile=profile
    )

    result = asyncio.run(
        service.run(
            project=r"C:\Projects\kis-mcp",
            exact_revision="9adf1ca26a6a96a173605a7e5dd5c11216d6ec0e",
            verification_id="python-pytest",
            timeout_ms=120_000,
        )
    )

    assert result.verification.status == "passed"
    assert result.verification.evidence == "proof ok"
    assert result.execution.backend_id == "windows-virtualbox"
    assert result.execution.image_id == profile.image_id
    commands = [str(arguments.get("command", "")) for _, arguments in runner.calls]
    assert any("clonevm" in command for command in commands)
    assert any("guestcontrol" in command and "'run'" in command for command in commands)
