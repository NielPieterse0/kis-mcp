from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from kis_mcp.execution.contracts import (
    ExecutionLifecycleState,
    ExecutionProfile,
    ExecutionRequest,
    ExecutionSource,
)
from kis_mcp.execution.settings import VirtualBoxProfileSettings
from kis_mcp.execution.virtualbox import VirtualBoxDisposableExecutionProvider


class _Runner:
    def __init__(
        self,
        state_root: Path,
        *,
        fail_fragment: str | None = None,
        fail_fragments: tuple[str, ...] = (),
        fail_text: str = "phase failed",
        template_config: str | None = None,
        template_extra: str = "",
        shared_folder: bool = False,
        snapshot_extra: str = "",
        snapshot_shared_folder: bool = False,
        omit_guest_result: bool = False,
    ) -> None:
        self.state_root = state_root
        self.fail_fragment = fail_fragment
        self.fail_fragments = fail_fragments
        self.fail_text = fail_text
        self.template_config = template_config
        self.template_extra = template_extra
        self.shared_folder = shared_folder
        self.snapshot_extra = snapshot_extra
        self.snapshot_shared_folder = snapshot_shared_folder
        self.omit_guest_result = omit_guest_result
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, tool: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((tool, arguments))
        command = str(arguments.get("command", ""))
        if self.fail_fragment and self.fail_fragment in command:
            return {"text": f"{self.fail_text}\n__KIS_EXECUTION_EXIT_CODE=1\n"}
        if any(fragment in command for fragment in self.fail_fragments):
            return {"text": f"{self.fail_text}\n__KIS_EXECUTION_EXIT_CODE=1\n"}
        if "'snapshot'" in command and "'showvminfo'" in command:
            config = self.template_config or str(
                self.state_root / "vbox-home" / "Machines" / "kis-windows-template.vbox"
            )
            shared = (
                "\nName: 'host-workspace', Host path: 'C:\\Users\\piete\\host-workspace'"
                if self.snapshot_shared_folder
                else ""
            )
            return {
                "text": (
                    f"Config file:     {config}{shared}{self.snapshot_extra}\n"
                    "__KIS_EXECUTION_EXIT_CODE=0\n"
                )
            }
        if "showvminfo" in command and "kis-windows-template" in command:
            config = self.template_config or str(
                self.state_root / "vbox-home" / "Machines" / "kis-windows-template.vbox"
            )
            shared = (
                '\nSharedFolderNameMachineMapping1="host-workspace"'
                if self.shared_folder
                else ""
            )
            return {
                "text": (
                    f'CfgFile="{config}"{shared}{self.template_extra}\n'
                    "__KIS_EXECUTION_EXIT_CODE=0\n"
                )
            }
        if "guestcontrol" in command and "'run'" in command:
            if self.omit_guest_result:
                return {"text": "guest command returned no result marker\n__KIS_EXECUTION_EXIT_CODE=0\n"}
            guest = json.dumps({"exit_code": 0, "stdout": "tests ok", "stderr": ""})
            return {"text": f"__KIS_GUEST_RESULT={guest}\n__KIS_EXECUTION_EXIT_CODE=0\n"}
        return {"text": "ok\n__KIS_EXECUTION_EXIT_CODE=0\n"}


def _config(tmp_path: Path) -> VirtualBoxProfileSettings:
    state_root = tmp_path / "virtualbox"
    return VirtualBoxProfileSettings(
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
    )


def _credentials(monkeypatch: Any, config: VirtualBoxProfileSettings) -> Path:
    password_file = Path(config.state_root) / "credentials" / "guest-password.txt"
    password_file.parent.mkdir(parents=True, exist_ok=True)
    password_file.write_text("s3cret", encoding="utf-8")
    monkeypatch.setenv(config.guest_username_env, "kis-runner")
    monkeypatch.setenv(config.guest_password_file_env, str(password_file))
    return password_file


def _provider(
    runner: _Runner, config: VirtualBoxProfileSettings
) -> VirtualBoxDisposableExecutionProvider:
    return VirtualBoxDisposableExecutionProvider(
        runner,
        config,
        profile_id="windows-virtualbox-proof",
        image_id="windows-virtualbox-proof-v1",
        toolchain_id="repository-declared-v1",
    )


def _request() -> ExecutionRequest:
    return ExecutionRequest(
        request_id="proof-324-virtualbox",
        project_id="kis-mcp",
        verification_profile_id="python",
        source=ExecutionSource(
            project_path=r"C:\Projects\kis-mcp",
            revision="9adf1ca26a6a96a173605a7e5dd5c11216d6ec0e",
            exact=True,
        ),
        profile=ExecutionProfile(
            profile_id="windows-virtualbox-proof",
            backend_id="windows-virtualbox",
            image_id="windows-virtualbox-proof-v1",
            toolchain_id="repository-declared-v1",
        ),
        executable="python",
        arguments=("-m", "pytest", "-q", "tests/test_contracts.py"),
        timeout_ms=120_000,
        evidence_limit_chars=20_000,
    )


def _commands(runner: _Runner) -> list[str]:
    return [str(arguments.get("command", "")) for _, arguments in runner.calls]


def test_virtualbox_orders_isolated_disposable_lifecycle_and_quarantines(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    runner = _Runner(Path(config.state_root))
    result = asyncio.run(_provider(runner, config).execute(_request()))

    commands = _commands(runner)
    fragments = [
        "--version",
        "showvminfo",
        "snapshot",
        "git -C",
        "clonevm",
        "--nic1=none",
        "startvm",
        "waitrunlevel",
        "'mkdir'",
        "copyto",
        "'run'",
        "poweroff",
        "--name=kis-quarantine-",
    ]
    positions = [
        next(i for i, command in enumerate(commands) if fragment in command)
        for fragment in fragments
    ]
    assert positions == sorted(positions)
    assert result.status == "passed"
    assert result.cleanup.value == "quarantined"
    assert result.lifecycle[-2:] == (
        ExecutionLifecycleState.QUARANTINED,
        ExecutionLifecycleState.COMPLETED,
    )
    assert result.evidence.stdout == "tests ok"
    assert result.evidence.receipt_path is not None
    receipt = Path(result.evidence.receipt_path)
    assert receipt.exists()
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["contract"] == "virtualbox-execution-receipt-v1"
    assert payload["source_revision"] == _request().source.revision
    assert all("VBOX_USER_HOME" in command for command in commands if "VBoxManage.exe" in command)
    assert all("unregistervm" not in command for command in commands)
    assert all("--delete" not in command for command in commands)
    assert all("s3cret" not in command for command in commands)


def test_virtualbox_repeated_request_allocates_fresh_attempt_state(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    runner = _Runner(Path(config.state_root))
    provider = _provider(runner, config)

    first = asyncio.run(provider.execute(_request()))
    second = asyncio.run(provider.execute(_request()))

    assert first.status == second.status == "passed"
    assert first.evidence.receipt_path != second.evidence.receipt_path
    namespaces = list((Path(config.state_root) / "requests").iterdir())
    assert len(namespaces) == 1
    assert [item.name for item in sorted(namespaces[0].iterdir())] == ["000001", "000002"]


def test_virtualbox_source_mismatch_stops_before_clone(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    runner = _Runner(
        Path(config.state_root),
        fail_fragment="git -C",
        fail_text=(
            "KIS_SOURCE_MISMATCH expected=9adf1ca26a6a96a173605a7e5dd5c11216d6ec0e "
            "actual=1111111111111111111111111111111111111111"
        ),
    )
    result = asyncio.run(_provider(runner, config).execute(_request()))

    assert result.status == "incomplete"
    assert result.failure_classification == "source_mismatch"
    assert not any("clonevm" in command for command in _commands(runner))


def test_virtualbox_unavailable_vboxmanage_stops_before_template_work(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    runner = _Runner(Path(config.state_root), fail_fragment="--version")
    result = asyncio.run(_provider(runner, config).execute(_request()))

    assert result.status == "incomplete"
    assert result.failure_classification == "backend_unavailable"
    commands = _commands(runner)
    assert len(commands) == 1
    assert "--version" in commands[0]
    assert not any("clonevm" in command for command in commands)


def test_virtualbox_rejects_template_outside_kis_state(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    runner = _Runner(
        Path(config.state_root),
        template_config=r"C:\Users\piete\VirtualBox VMs\kis-windows-template.vbox",
    )
    result = asyncio.run(_provider(runner, config).execute(_request()))

    assert result.status == "incomplete"
    assert result.failure_classification == "backend_unavailable"
    assert not any("clonevm" in command for command in _commands(runner))


def test_virtualbox_rejects_template_media_outside_kis_state(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    runner = _Runner(
        Path(config.state_root),
        template_extra='\nSATA-0-0="C:\\Users\\piete\\VirtualBox VMs\\template.vdi"',
    )
    result = asyncio.run(_provider(runner, config).execute(_request()))

    assert result.status == "incomplete"
    assert result.failure_classification == "backend_unavailable"
    assert not any("clonevm" in command for command in _commands(runner))


def test_virtualbox_rejects_snapshot_media_outside_kis_state(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    runner = _Runner(
        Path(config.state_root),
        snapshot_extra=(
            "\nSATA (0, 0): C:\\Users\\piete\\VirtualBox VMs\\snapshot.vdi "
            "(UUID: 11111111-1111-1111-1111-111111111111)"
        ),
    )
    result = asyncio.run(_provider(runner, config).execute(_request()))

    assert result.status == "incomplete"
    assert result.failure_classification == "backend_unavailable"
    assert not any("clonevm" in command for command in _commands(runner))


def test_virtualbox_rejects_snapshot_shared_folders(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    runner = _Runner(Path(config.state_root), snapshot_shared_folder=True)
    result = asyncio.run(_provider(runner, config).execute(_request()))

    assert result.status == "incomplete"
    assert result.failure_classification == "backend_unavailable"
    assert not any("clonevm" in command for command in _commands(runner))


def test_virtualbox_rejects_template_shared_folders(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    runner = _Runner(Path(config.state_root), shared_folder=True)
    result = asyncio.run(_provider(runner, config).execute(_request()))

    assert result.status == "incomplete"
    assert result.failure_classification == "backend_unavailable"
    assert not any("clonevm" in command for command in _commands(runner))


def test_virtualbox_missing_guest_credentials_fails_before_vbox_work(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    monkeypatch.delenv(config.guest_username_env, raising=False)
    monkeypatch.delenv(config.guest_password_file_env, raising=False)
    runner = _Runner(Path(config.state_root))
    result = asyncio.run(_provider(runner, config).execute(_request()))

    assert result.status == "incomplete"
    assert result.failure_classification == "backend_unavailable"
    assert runner.calls == []


def test_virtualbox_password_file_must_remain_inside_provider_state(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    outside_password = tmp_path / "outside-password.txt"
    outside_password.write_text("s3cret", encoding="utf-8")
    monkeypatch.setenv(config.guest_username_env, "kis-runner")
    monkeypatch.setenv(config.guest_password_file_env, str(outside_password))
    runner = _Runner(Path(config.state_root))
    result = asyncio.run(_provider(runner, config).execute(_request()))

    assert result.status == "incomplete"
    assert result.failure_classification == "backend_unavailable"
    assert runner.calls == []


def test_virtualbox_failed_clone_does_not_mask_primary_failure_as_cleanup_failure(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    runner = _Runner(
        Path(config.state_root),
        fail_fragments=("clonevm", "controlvm", "--name=kis-quarantine-"),
    )
    result = asyncio.run(_provider(runner, config).execute(_request()))

    assert result.status == "incomplete"
    assert result.cleanup.value == "failed"
    assert result.failure_classification == "lifecycle_failed"


def test_virtualbox_guest_control_failure_is_incomplete_and_quarantined(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    runner = _Runner(Path(config.state_root), fail_fragment="copyto")
    result = asyncio.run(_provider(runner, config).execute(_request()))

    assert result.status == "incomplete"
    assert result.failure_classification == "lifecycle_failed"
    assert result.cleanup.value == "quarantined"
    assert not any("'run'" in command for command in _commands(runner))


def test_virtualbox_missing_guest_result_is_incomplete_and_quarantined(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    runner = _Runner(Path(config.state_root), omit_guest_result=True)
    result = asyncio.run(_provider(runner, config).execute(_request()))

    assert result.status == "incomplete"
    assert result.failure_classification == "timeout_or_incomplete"
    assert result.cleanup.value == "quarantined"


def test_virtualbox_receipt_write_failure_returns_incomplete(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    runner = _Runner(Path(config.state_root))
    provider = _provider(runner, config)

    def fail_receipt(*args: Any, **kwargs: Any) -> None:
        raise OSError("receipt write failed")

    monkeypatch.setattr(provider, "_write_receipt", fail_receipt)
    result = asyncio.run(provider.execute(_request()))

    assert result.status == "incomplete"
    assert result.failure_classification == "lifecycle_failed"
    assert result.evidence.receipt_path is None
    assert result.lifecycle[-1] == ExecutionLifecycleState.INCOMPLETE


def test_virtualbox_cleanup_failure_cannot_return_passed(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    runner = _Runner(
        Path(config.state_root), fail_fragment="--name=kis-quarantine-"
    )
    result = asyncio.run(_provider(runner, config).execute(_request()))

    assert result.status == "incomplete"
    assert result.cleanup.value == "failed"
    assert result.failure_classification == "cleanup_failed"
    assert result.lifecycle[-1] == ExecutionLifecycleState.INCOMPLETE


def test_virtualbox_profile_identity_mismatch_fails_before_host_work(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = _config(tmp_path)
    _credentials(monkeypatch, config)
    request = _request()
    mismatched = ExecutionRequest(
        request_id=request.request_id,
        project_id=request.project_id,
        verification_profile_id=request.verification_profile_id,
        source=request.source,
        profile=ExecutionProfile(
            profile_id=request.profile.profile_id,
            backend_id=request.profile.backend_id,
            image_id="stale-image-v0",
            toolchain_id=request.profile.toolchain_id,
        ),
        executable=request.executable,
        arguments=request.arguments,
        timeout_ms=request.timeout_ms,
        evidence_limit_chars=request.evidence_limit_chars,
    )
    runner = _Runner(Path(config.state_root))
    result = asyncio.run(_provider(runner, config).execute(mismatched))

    assert result.status == "incomplete"
    assert result.failure_classification == "profile_identity_mismatch"
    assert runner.calls == []
