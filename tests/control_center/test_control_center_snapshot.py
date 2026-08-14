from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from kis_mcp.control_center.settings import ControlCenterSettings
from kis_mcp.control_center.snapshot import ControlCenterSnapshotService


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def _settings(tmp_path: Path, project: Path) -> ControlCenterSettings:
    runtime_path = tmp_path / "runtime.json"
    policy_path = tmp_path / "policy.json"
    providers_path = tmp_path / "providers.json"
    quarantine_root = tmp_path / "quarantine"

    _write_json(
        runtime_path,
        {
            "schema_version": 1,
            "product": {"name": "kis-mcp"},
            "desktop_commander": {
                "version": "0.2.46",
                "entry_point": "node_modules/@wonderwhy-er/desktop-commander/dist/index.js",
                "launch": {"cwd": str(tmp_path / "desktop-commander")},
            },
            "fastmcp": {"server_name": "kis-mcp"},
            "implementation_status": {
                "policy_core": "diagnostic_unit_verified",
                "live_proxy": "verified_stdio_and_dual_streamable_http",
            },
        },
    )
    _write_json(
        policy_path,
        {
            "schema_version": 1,
            "rules": [
                {
                    "id": "HR-001",
                    "name": "Write boundary",
                    "prohibited_outcome": "write outside C:\\Projects",
                    "decision": "block",
                },
                {
                    "id": "HR-002",
                    "name": "External network",
                    "prohibited_outcome": "external network through Work",
                    "decision": "block",
                },
                {
                    "id": "HR-003",
                    "name": "Permanent deletion",
                    "prohibited_outcome": "permanent deletion",
                    "decision": "quarantine",
                },
            ]
        },
    )
    _write_json(
        providers_path,
        {
            "schema_version": 1,
            "providers": [
                {
                    "provider_id": "github-mcp",
                    "enabled": True,
                    "namespace": "github",
                },
                {
                    "provider_id": "supabase",
                    "enabled": True,
                    "namespace": "supabase",
                },
            ]
        },
    )
    quarantine_root.mkdir()
    _write_json(
        quarantine_root / "20260805T010203000000Z-aaaaaaaaaaaa" / "metadata.json",
        {
            "schema_version": 2,
            "operation_id": "20260805T010203000000Z-aaaaaaaaaaaa",
            "original_path": r"C:\Projects\active.txt",
            "item_type": "file",
            "restored_at": None,
        },
    )
    _write_json(
        quarantine_root / "20260805T010204000000Z-bbbbbbbbbbbb" / "metadata.json",
        {
            "schema_version": 2,
            "operation_id": "20260805T010204000000Z-bbbbbbbbbbbb",
            "original_path": r"C:\Projects\restored.txt",
            "item_type": "file",
            "restored_at": "2026-08-05T01:03:00+00:00",
        },
    )
    _write_json(
        quarantine_root / "20260805T010205000000Z-cccccccccccc" / "metadata.json",
        {
            "schema_version": 2,
            "operation_id": "20260805T010205000000Z-cccccccccccc",
            "original_path": r"C:\Projects\invalid.txt",
            "item_type": "file",
            "restored_at": 7,
        },
    )

    return ControlCenterSettings(
        schema_version=1,
        project_path=project,
        runtime_settings_path=runtime_path,
        policy_path=policy_path,
        provider_settings_path=providers_path,
        quarantine_root=quarantine_root,
        verification_command=(
            "pwsh",
            "-NoProfile",
            "-File",
            "scripts/verify.ps1",
        ),
        max_provider_entries=20,
        max_quarantine_records=20,
        git_timeout_seconds=3,
        max_json_bytes=1_000_000,
    )


def _initialize_dirty_repository(project: Path) -> None:
    project.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    (project / "README.md").write_text("local change\n", encoding="utf-8")


def test_snapshot_collects_bounded_truthful_local_status(tmp_path: Path) -> None:
    project = tmp_path / "project"
    _initialize_dirty_repository(project)
    settings = _settings(tmp_path, project)

    snapshot = ControlCenterSnapshotService(settings).collect()

    assert snapshot.runtime.product == "kis-mcp"
    assert snapshot.runtime.server == "kis-mcp"
    assert snapshot.runtime.desktop_commander_version == "0.2.46"
    assert snapshot.runtime.desktop_commander_installed is False
    assert snapshot.project.path == str(project)
    assert snapshot.project.git.status == "available"
    assert snapshot.project.git.branch == "main"
    assert snapshot.project.git.dirty is True
    assert snapshot.project.git.changed_files == 1
    assert snapshot.policy.closed_rule_set is True
    assert [rule.rule_id for rule in snapshot.policy.rules] == [
        "HR-001",
        "HR-002",
        "HR-003",
    ]
    assert [provider.provider_id for provider in snapshot.providers] == [
        "github-mcp",
        "supabase",
    ]
    assert all(
        provider.readiness == "runtime_check_required"
        for provider in snapshot.providers
    )
    assert snapshot.quarantine.total_records == 3
    assert snapshot.quarantine.active_records == 1
    assert snapshot.quarantine.restored_records == 1
    assert snapshot.quarantine.invalid_records == 1
    assert snapshot.verification.status == "not_recorded"
    assert snapshot.verification.command[-1] == "scripts/verify.ps1"
    assert snapshot.generated_at.endswith("+00:00")
    assert snapshot.work_board["status"] == "unavailable"


def test_snapshot_preserves_unknown_states_instead_of_failing(tmp_path: Path) -> None:
    project = tmp_path / "not-a-repository"
    project.mkdir()
    settings = _settings(tmp_path, project)
    settings.runtime_settings_path.unlink()
    settings.provider_settings_path.write_text("not-json", encoding="utf-8")

    snapshot = ControlCenterSnapshotService(settings).collect()

    assert snapshot.runtime.status == "unavailable"
    assert snapshot.project.git.status == "not_repository"
    assert snapshot.providers == ()
    assert any(
        diagnostic.code == "CONTROL_CENTER_RUNTIME_SETTINGS_UNAVAILABLE"
        for diagnostic in snapshot.diagnostics
    )
    assert any(
        diagnostic.code == "CONTROL_CENTER_PROVIDER_SETTINGS_INVALID"
        for diagnostic in snapshot.diagnostics
    )
    assert snapshot.verification.status == "not_recorded"


def test_snapshot_ignores_inherited_git_repository_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    external_repository = tmp_path / "external-repository"
    _initialize_dirty_repository(external_repository)
    project = tmp_path / "plain-directory"
    project.mkdir()
    settings = _settings(tmp_path / "settings", project)
    monkeypatch.setenv("GIT_DIR", str(external_repository / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(external_repository))

    snapshot = ControlCenterSnapshotService(settings).collect()

    assert snapshot.project.git.status == "not_repository"
    assert snapshot.project.git.branch is None


def test_structured_snapshot_keeps_work_board_explicitly_unavailable_without_injection(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    _initialize_dirty_repository(project)
    snapshot = ControlCenterSnapshotService(_settings(tmp_path, project)).collect()

    structured = snapshot.to_dict()

    assert structured["work_board"] == {
        "schema_version": 1,
        "status": "unavailable",
        "reason": "no_authoritative_board_read_observed_in_process",
        "authority": "configured_work_management_backend",
    }
