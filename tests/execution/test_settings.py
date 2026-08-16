from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.execution.settings import (
    ExecutionSettingsError,
    HyperVProfileSettings,
    load_execution_runner_settings,
)


def test_repository_execution_settings_default_to_local_process() -> None:
    settings = load_execution_runner_settings()
    default = settings.profile(settings.default_profile)

    assert default.profile_id == "local-process"
    assert default.backend_id == "local-process"
    assert default.enabled is True
    proof = settings.profile("windows-hyperv-proof")
    assert proof.backend_id == "windows-hyperv"
    assert proof.enabled is False
    assert proof.hyperv is not None
    assert proof.hyperv.checkpoint_name


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
