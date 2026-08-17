from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.execution.settings import (
    ExecutionSettingsError,
    HyperVProfileSettings,
    LocalProcessProfileSettings,
    load_execution_runner_settings,
)


def _with_virtualbox_profile(payload: dict[str, object]) -> dict[str, object]:
    profiles = payload["profiles"]
    assert isinstance(profiles, list)
    profiles.append(
        {
            "profile_id": "windows-virtualbox-proof",
            "backend_id": "windows-virtualbox",
            "enabled": False,
            "image_id": "windows-virtualbox-proof-v1",
            "toolchain_id": "repository-declared-v1",
            "virtualbox": {
                "vboxmanage_path": r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
                "template_vm": "kis-windows-template",
                "snapshot_name": "clean",
                "state_root": r"C:\Projects\.kis-mcp\execution\virtualbox",
                "vbox_user_home": r"C:\Projects\.kis-mcp\execution\virtualbox\vbox-home",
                "guest_workspace": r"C:\KIS\workspace",
                "guest_username_env": "KIS_VIRTUALBOX_GUEST_USERNAME",
                "guest_password_file_env": "KIS_VIRTUALBOX_GUEST_PASSWORD_FILE",
                "startup_timeout_ms": 120000,
                "cleanup_timeout_ms": 60000,
            },
        }
    )
    return payload


def test_repository_execution_settings_default_to_local_process() -> None:
    settings = load_execution_runner_settings()
    default = settings.profile(settings.default_profile)

    assert default.profile_id == "local-process"
    assert default.backend_id == "local-process"
    assert default.enabled is True
    assert default.local is not None
    assert default.local.state_root == r"C:\Projects\.kis-mcp\execution\local"
    assert default.local.worker_cleanup_grace_ms == 10_000
    hyperv = settings.profile("windows-hyperv-proof")
    assert hyperv.backend_id == "windows-hyperv"
    assert hyperv.enabled is False
    assert hyperv.hyperv is not None
    assert hyperv.hyperv.checkpoint_name

    virtualbox = settings.profile("windows-virtualbox-proof")
    assert virtualbox.backend_id == "windows-virtualbox"
    assert virtualbox.enabled is False
    assert virtualbox.virtualbox is not None
    assert virtualbox.virtualbox.snapshot_name == "clean"
    assert virtualbox.virtualbox.vbox_user_home.startswith(r"C:\Projects\.kis-mcp")


def test_execution_settings_reject_unknown_keys(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "settings" / "execution-runners.settings.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["surprise"] = True
    target = tmp_path / "execution.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExecutionSettingsError, match="unknown"):
        load_execution_runner_settings(target)


def test_execution_settings_reject_state_root_outside_kis_state_boundary(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "settings" / "execution-runners.settings.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["profiles"][1]["hyperv"]["state_root"] = r"C:\ProgramData\kis-mcp\hyperv"
    target = tmp_path / "execution.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExecutionSettingsError, match="KIS state root"):
        load_execution_runner_settings(target)


def test_direct_local_settings_reject_state_root_outside_kis_boundary() -> None:
    with pytest.raises(ExecutionSettingsError, match="KIS state root"):
        LocalProcessProfileSettings(
            state_root=r"C:\ProgramData\kis-mcp\local",
            materialize_timeout_ms=60_000,
            worker_cleanup_grace_ms=10_000,
        )


def test_direct_hyperv_settings_reject_state_root_outside_kis_boundary() -> None:
    with pytest.raises(ExecutionSettingsError, match="KIS state root"):
        HyperVProfileSettings(
            template_vm="kis-windows-template",
            checkpoint_name="clean",
            state_root=r"C:\ProgramData\kis-mcp\hyperv",
            guest_workspace=r"C:\KIS\workspace",
            guest_username_env="KIS_HYPERV_GUEST_USERNAME",
            guest_password_env="KIS_HYPERV_GUEST_PASSWORD",
            startup_timeout_ms=60_000,
            cleanup_timeout_ms=30_000,
        )


def test_virtualbox_settings_reject_state_root_outside_kis_boundary(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "settings" / "execution-runners.settings.json"
    payload = _with_virtualbox_profile(json.loads(source.read_text(encoding="utf-8")))
    profiles = payload["profiles"]
    assert isinstance(profiles, list)
    profiles[-1]["virtualbox"]["state_root"] = r"C:\ProgramData\kis-mcp\virtualbox"
    target = tmp_path / "execution.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExecutionSettingsError, match="KIS state root"):
        load_execution_runner_settings(target)


def test_virtualbox_settings_reject_vbox_home_outside_profile_state_root(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "settings" / "execution-runners.settings.json"
    payload = _with_virtualbox_profile(json.loads(source.read_text(encoding="utf-8")))
    profiles = payload["profiles"]
    assert isinstance(profiles, list)
    profiles[-1]["virtualbox"]["vbox_user_home"] = r"C:\Projects\.kis-mcp\other-vbox-home"
    target = tmp_path / "execution.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExecutionSettingsError, match="virtualbox state root"):
        load_execution_runner_settings(target)
