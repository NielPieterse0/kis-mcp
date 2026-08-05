from __future__ import annotations

import json
from pathlib import Path

from kis_mcp.control_center.contracts import Diagnostic
from kis_mcp.control_center.readers import (
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
