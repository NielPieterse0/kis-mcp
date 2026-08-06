from __future__ import annotations

import json
from pathlib import Path

from kis_mcp.control_center.settings import ControlCenterSettings
from kis_mcp.control_center.snapshot import ControlCenterSnapshotService


def test_snapshot_rejects_json_input_above_configured_byte_limit(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    runtime_path = tmp_path / "runtime.json"
    runtime_path.write_bytes(b"{" + (b"x" * 2048) + b"}")
    settings = ControlCenterSettings(
        schema_version=1,
        project_path=project,
        runtime_settings_path=runtime_path,
        policy_path=tmp_path / "policy.json",
        provider_settings_path=tmp_path / "providers.json",
        quarantine_root=tmp_path / "quarantine",
        verification_command=("pwsh", "-File", "scripts/verify.ps1"),
        max_provider_entries=20,
        max_quarantine_records=20,
        git_timeout_seconds=3,
        max_json_bytes=1024,
    )

    snapshot = ControlCenterSnapshotService(settings).collect()

    assert snapshot.runtime.status == "unavailable"
    assert any(
        diagnostic.code == "CONTROL_CENTER_RUNTIME_SETTINGS_INVALID_LIMIT_EXCEEDED"
        for diagnostic in snapshot.diagnostics
    )


def test_snapshot_applies_json_byte_limit_to_quarantine_metadata(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    runtime_path = tmp_path / "runtime.json"
    policy_path = tmp_path / "policy.json"
    providers_path = tmp_path / "providers.json"
    runtime_path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    policy_path.write_text(json.dumps({"schema_version": 1, "rules": []}), encoding="utf-8")
    providers_path.write_text(json.dumps({"schema_version": 1, "providers": []}), encoding="utf-8")
    quarantine_root = tmp_path / "quarantine"
    metadata_path = (
        quarantine_root
        / "20260805T010203000000Z-aaaaaaaaaaaa"
        / "metadata.json"
    )
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "operation_id": "20260805T010203000000Z-aaaaaaaaaaaa",
                "original_path": r"C:\Projects\large.txt",
                "item_type": "file",
                "restored_at": None,
                "padding": "x" * 2048,
            }
        ),
        encoding="utf-8",
    )
    settings = ControlCenterSettings(
        schema_version=1,
        project_path=project,
        runtime_settings_path=runtime_path,
        policy_path=policy_path,
        provider_settings_path=providers_path,
        quarantine_root=quarantine_root,
        verification_command=("pwsh", "-File", "scripts/verify.ps1"),
        max_provider_entries=20,
        max_quarantine_records=20,
        git_timeout_seconds=3,
        max_json_bytes=1024,
    )

    snapshot = ControlCenterSnapshotService(settings).collect()

    assert snapshot.quarantine.active_records == 0
    assert snapshot.quarantine.invalid_records == 1
    assert any(
        diagnostic.code == "CONTROL_CENTER_QUARANTINE_METADATA_INVALID_LIMIT_EXCEEDED"
        for diagnostic in snapshot.diagnostics
    )
