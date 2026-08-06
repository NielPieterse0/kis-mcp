from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from kis_mcp.control_center.settings import ControlCenterSettings
from kis_mcp.control_center.snapshot import ControlCenterSnapshotService
from kis_mcp.runtime_observability import RuntimeObservability


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _settings(tmp_path: Path) -> ControlCenterSettings:
    runtime = tmp_path / "runtime.json"
    policy = tmp_path / "policy.json"
    providers = tmp_path / "providers.json"
    approvals = tmp_path / "HARD-BLOCK-APPROVAL-REGISTER.md"
    project = tmp_path / "project"
    quarantine = tmp_path / "quarantine"
    project.mkdir()
    _write_json(
        runtime,
        {
            "schema_version": 1,
            "product": {"name": "kis-mcp"},
            "fastmcp": {"server_name": "kis-mcp"},
        },
    )
    _write_json(
        policy,
        {
            "schema_version": 1,
            "rules": [
                {"id": "HR-001", "name": "Write boundary", "prohibited_outcome": "outside writes", "decision": "block"},
                {"id": "HR-002", "name": "External network", "prohibited_outcome": "external network", "decision": "block"},
                {"id": "HR-003", "name": "Permanent deletion", "prohibited_outcome": "permanent deletion", "decision": "quarantine"},
            ]
        },
    )
    _write_json(
        providers,
        {
            "schema_version": 1,
            "providers": [
                {"provider_id": "github-mcp", "enabled": True, "namespace": "github"},
                {"provider_id": "control-center", "enabled": True, "namespace": "controlcenter"},
            ]
        },
    )
    approvals.write_text(
        """# Hard Block Approval Register\n\n## HR1-01 — Outside write resolver\n\n**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject\n\nReason: Needs bounded resolver evidence.\n\n## HR2-01 — Network provider\n\n**Operator decision:** [x] Approve  [ ] Revise  [ ] Reject\n\n## HR3-01 — Deletion wording\n\n**Operator decision:** [ ] Approve  [x] Revise  [ ] Reject\n""",
        encoding="utf-8",
    )
    operation = quarantine / "20260805T010203000000Z-aaaaaaaaaaaa"
    _write_json(
        operation / "metadata.json",
        {
            "operation_id": operation.name,
            "schema_version": 2,
            "original_path": r"C:\Projects\old.txt",
            "item_type": "file",
            "restored_at": None,
        },
    )
    return ControlCenterSettings(
        schema_version=1,
        project_path=project,
        runtime_settings_path=runtime,
        policy_path=policy,
        provider_settings_path=providers,
        approval_register_path=approvals,
        quarantine_root=quarantine,
        verification_command=("pwsh", "-File", "scripts/verify.ps1"),
        discover_enabled=True,
        max_provider_entries=20,
        max_approval_entries=10,
        max_recent_calls=10,
        max_policy_decisions=10,
        max_active_processes=10,
        max_active_searches=10,
        max_discover_findings=10,
        max_quarantine_records=10,
        git_timeout_seconds=3,
        max_json_bytes=1_000_000,
    )


def test_enriched_snapshot_projects_approvals_discover_providers_and_runtime_state(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    observability = RuntimeObservability(max_recent_calls=10, max_policy_decisions=10)
    observability.record_tool_call(
        tool_name="write_file",
        argument_keys=("path", "content"),
        decision="block",
        outcome="rejected",
        code="HR-001_WRITE_OUTSIDE_PROJECTS",
    )
    observability.process_started(pid=42, cwd=str(settings.project_path), shell="powershell")
    observability.search_started(search_id="search-1", tool_name="start_search")

    service = ControlCenterSnapshotService(
        settings,
        observability=observability,
        discover_source=lambda: {
            "status": "available",
            "project_id": "project-1",
            "languages": ["Python"],
            "frameworks": ["FastMCP"],
            "module_count": 8,
            "finding_count": 2,
            "confidence": "high",
            "truncated": False,
            "findings": ["Finding A", "Finding B"],
        },
        provider_status_source=lambda: {
            "external_providers": [
                {
                    "provider_id": "control-center",
                    "namespace": "controlcenter",
                    "registered": True,
                    "enabled": True,
                    "mounted": True,
                    "state": "mounted",
                    "readiness": {"state": "ready", "summary": "Local UI ready."},
                    "user_status": None,
                    "commissioning": {"live_verified": "not_applicable"},
                },
                {
                    "provider_id": "github-mcp",
                    "namespace": "github",
                    "registered": True,
                    "enabled": True,
                    "mounted": True,
                    "state": "mounted",
                    "readiness": {"state": "ready", "summary": "Authentication required."},
                    "user_status": {"required_action": "Authenticate before live operations."},
                    "commissioning": {"authenticated": "required"},
                },
            ]
        },
    )

    snapshot = service.collect()

    assert [(item.approval_id, item.title) for item in snapshot.approvals] == [
        ("HR1-01", "Outside write resolver")
    ]
    assert snapshot.discover.status == "available"
    assert snapshot.discover.languages == ("Python",)
    assert snapshot.discover.findings == ("Finding A", "Finding B")
    assert [item.provider_id for item in snapshot.provider_runtime] == [
        "control-center",
        "github-mcp",
    ]
    assert snapshot.provider_runtime[0].mounted is True
    assert snapshot.provider_runtime[1].action == "Authenticate before live operations."
    assert [item.tool_name for item in snapshot.observability.recent_calls] == ["write_file"]
    assert [item.pid for item in snapshot.observability.active_processes] == [42]
    assert [item.search_id for item in snapshot.observability.active_searches] == ["search-1"]
    assert snapshot.quarantine_records[0].operation_id.endswith("aaaaaaaaaaaa")
    assert {item.tool_name for item in snapshot.actions} >= {
        "kis_list_quarantine",
        "kis_restore_quarantine",
        "inspect_project",
    }


def test_enriched_snapshot_degrades_failed_sources_without_losing_other_sections(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    def fail_discover() -> dict[str, object]:
        raise RuntimeError("private discover failure detail")

    snapshot = ControlCenterSnapshotService(
        settings,
        discover_source=fail_discover,
        provider_status_source=lambda: {},
    ).collect()

    assert snapshot.runtime.product == "kis-mcp"
    assert snapshot.policy.closed_rule_set is True
    assert snapshot.discover.status == "unavailable"
    assert snapshot.provider_runtime == ()
    rendered = str(snapshot.to_dict())
    assert "private discover failure detail" not in rendered
    assert any(item.code == "CONTROL_CENTER_DISCOVER_UNAVAILABLE" for item in snapshot.diagnostics)


def test_approval_register_is_byte_bounded(tmp_path: Path) -> None:
    settings = replace(_settings(tmp_path), max_json_bytes=1024)
    settings.approval_register_path.write_text("x" * 2048, encoding="utf-8")

    snapshot = ControlCenterSnapshotService(
        settings,
        discover_source=lambda: {},
        provider_status_source=lambda: {},
    ).collect()

    assert snapshot.approvals == ()
    assert any(
        item.code == "CONTROL_CENTER_APPROVAL_REGISTER_LIMIT_EXCEEDED"
        for item in snapshot.diagnostics
    )
