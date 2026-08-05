from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from kis_mcp.control_center.contracts import Diagnostic
from kis_mcp.control_center.readers import (
    GitStatusReader,
    PolicyStatusReader,
    ProviderStatusReader,
    QuarantineStatusReader,
    RuntimeStatusReader,
)
from kis_mcp.control_center.settings import ControlCenterSettings


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def _settings(tmp_path: Path) -> ControlCenterSettings:
    project = tmp_path / "project"
    project.mkdir()
    return ControlCenterSettings(
        schema_version=1,
        project_path=project,
        runtime_settings_path=tmp_path / "runtime.json",
        policy_path=tmp_path / "policy.json",
        provider_settings_path=tmp_path / "providers.json",
        quarantine_root=tmp_path / "quarantine",
        verification_command=("pwsh", "-File", "scripts/verify.ps1"),
        max_provider_entries=20,
        max_quarantine_records=20,
        git_timeout_seconds=3,
        max_json_bytes=1_000_000,
    )


def test_runtime_reader_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_json(
        settings.runtime_settings_path,
        {
            "schema_version": 2,
            "product": {"name": "wrong"},
            "fastmcp": {"server_name": "wrong"},
        },
    )
    diagnostics: list[Diagnostic] = []

    summary = RuntimeStatusReader(settings).read(diagnostics)

    assert summary.status == "unavailable"
    assert summary.product == "unknown"
    assert [item.code for item in diagnostics] == [
        "CONTROL_CENTER_RUNTIME_SETTINGS_INVALID"
    ]


def test_policy_and_provider_readers_require_schema_version_one(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_json(settings.policy_path, {"rules": []})
    _write_json(settings.provider_settings_path, {"schema_version": 7, "providers": []})
    diagnostics: list[Diagnostic] = []

    policy = PolicyStatusReader(settings).read(diagnostics)
    providers = ProviderStatusReader(settings).read(diagnostics)

    assert policy.status == "unavailable"
    assert policy.rules == ()
    assert providers == ()
    assert [item.code for item in diagnostics] == [
        "CONTROL_CENTER_POLICY_INVALID",
        "CONTROL_CENTER_PROVIDER_SETTINGS_INVALID",
    ]


def test_quarantine_reader_counts_unsupported_metadata_schema_as_invalid(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    operation_id = "20260805T010203000000Z-aaaaaaaaaaaa"
    _write_json(
        settings.quarantine_root / operation_id / "metadata.json",
        {
            "schema_version": 1,
            "operation_id": operation_id,
            "original_path": r"C:\Projects\old.txt",
            "item_type": "file",
            "restored_at": None,
        },
    )
    diagnostics: list[Diagnostic] = []

    summary, records = QuarantineStatusReader(settings).read(diagnostics)

    assert summary.total_records == 1
    assert summary.invalid_records == 1
    assert records == ()
    assert [item.code for item in diagnostics] == [
        "CONTROL_CENTER_QUARANTINE_METADATA_INVALID"
    ]


def test_runtime_reader_prefers_desktop_commander_launch_argument(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    entry = tmp_path / "desktop-commander" / "dist" / "index.js"
    entry.parent.mkdir(parents=True)
    entry.write_text("// test", encoding="utf-8")
    _write_json(
        settings.runtime_settings_path,
        {
            "schema_version": 1,
            "desktop_commander": {
                "version": "0.2.46",
                "entry_point": "missing.js",
                "launch": {
                    "cwd": str(tmp_path / "wrong"),
                    "args": [str(entry)],
                },
            },
        },
    )
    diagnostics: list[Diagnostic] = []

    summary = RuntimeStatusReader(settings).read(diagnostics)

    assert summary.product == "unknown"
    assert summary.desktop_commander_installed is True
    assert diagnostics == []


def test_policy_reader_preserves_mismatch_diagnostic_and_invalid_empty_state(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    _write_json(settings.policy_path, {"schema_version": 1, "rules": []})
    diagnostics: list[Diagnostic] = []

    summary = PolicyStatusReader(settings).read(diagnostics)

    assert summary.status == "invalid"
    assert summary.closed_rule_set is False
    assert [item.code for item in diagnostics] == [
        "CONTROL_CENTER_POLICY_RULE_SET_MISMATCH"
    ]


def test_provider_reader_preserves_declared_order_and_runtime_status_action(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    _write_json(
        settings.provider_settings_path,
        {
            "schema_version": 1,
            "providers": [
                {"provider_id": "z-provider", "enabled": False},
                {
                    "provider_id": "a-provider",
                    "namespace": "alpha",
                    "enabled": True,
                },
            ],
        },
    )
    diagnostics: list[Diagnostic] = []

    summaries = ProviderStatusReader(settings).read(diagnostics)

    assert [item.provider_id for item in summaries] == ["z-provider", "a-provider"]
    assert summaries[0].namespace == "unknown"
    assert summaries[0].readiness == "runtime_check_required"
    assert summaries[0].action.startswith("Use kis_provider_status")
    assert diagnostics == []


def test_git_reader_preserves_fixed_local_command_and_isolated_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setenv("GIT_DIR", "forbidden")
    monkeypatch.setenv("GIT_ALTERNATE_OBJECT_DIRECTORIES", "forbidden")
    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed["command"] = command
        observed["environment"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0, "## main\n M file.txt\n", "")

    monkeypatch.setattr("kis_mcp.control_center.readers.subprocess.run", fake_run)

    summary = GitStatusReader(settings).read()

    assert observed["command"] == [
        "git",
        "-C",
        str(settings.project_path),
        "status",
        "--short",
        "--branch",
        "--untracked-files=normal",
    ]
    environment = observed["environment"]
    assert isinstance(environment, dict)
    assert "GIT_DIR" not in environment
    assert "GIT_ALTERNATE_OBJECT_DIRECTORIES" not in environment
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert environment["GIT_OPTIONAL_LOCKS"] == "0"
    assert summary.branch == "main"
    assert summary.dirty is True
    assert summary.changed_files == 1
