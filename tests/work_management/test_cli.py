from __future__ import annotations

import json
from pathlib import Path

from kis_mcp.project_workflow_cli import main


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def settings_document(root: Path) -> dict[str, object]:
    return {
        "schema_version": 1,
        "enabled": True,
        "portfolio_id": "default",
        "managed_projects": [
            {
                "project_id": "alpha-project",
                "local_root": str(root),
                "repository": "ExampleOwner/alpha",
                "backend_binding": "github-default",
                "display_name": "Alpha",
            }
        ],
        "backend_bindings": [
            {
                "binding_id": "github-default",
                "provider": "github-mcp",
                "owner": "ExampleOwner",
                "owner_type": "user",
                "project_number": 12,
            }
        ],
        "features": {"programme_status": "enabled"},
        "automation": {"scheduled_reconciliation": False},
        "gates": {"change_traceability": "required"},
        "evidence": {"max_file_bytes": 1024, "max_total_bytes": 4096},
    }


def test_settings_command_emits_bounded_json_and_revision(
    tmp_path: Path,
    capsys,
) -> None:
    settings = write_json(tmp_path / "settings.json", settings_document(tmp_path))

    exit_code = main(
        [
            "settings",
            "--settings",
            str(settings),
            "--revision",
            "abc1234",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["revision"] == "abc1234"
    assert payload["settings"]["portfolio_id"] == "default"


def test_reconcile_command_defaults_to_preview_and_rejects_apply_without_key(
    tmp_path: Path,
    capsys,
) -> None:
    desired = write_json(
        tmp_path / "desired.json",
        [
            {
                "project_id": "alpha-project",
                "record_id": "TASK-1",
                "fields": {"Status": "Active"},
                "expected_revision": "rev-1",
                "source_repository": "ExampleOwner/alpha",
                "source_number": 7,
                "source_kind": "issue",
            }
        ],
    )
    observed = write_json(
        tmp_path / "observed.json",
        [
            {
                "project_id": "alpha-project",
                "record_id": "TASK-1",
                "fields": {"Status": "Inbox"},
                "revision": "rev-1",
                "accessible": True,
                "external_id": "I_1",
            }
        ],
    )

    preview_code = main(
        [
            "reconcile",
            "--desired",
            str(desired),
            "--observed",
            str(observed),
            "--supported-field",
            "Status",
            "--revision",
            "abc1234",
        ]
    )
    preview = json.loads(capsys.readouterr().out)

    assert preview_code == 0
    assert preview["mode"] == "preview"
    assert preview["decisions"][0]["action"] == "update"

    apply_code = main(
        [
            "reconcile",
            "--desired",
            str(desired),
            "--observed",
            str(observed),
            "--supported-field",
            "Status",
            "--apply",
        ]
    )
    failure = json.loads(capsys.readouterr().out)
    assert apply_code == 2
    assert failure["error_code"] == "idempotency_key_required"


def test_verify_traceability_reports_exact_stage_result(tmp_path: Path, capsys) -> None:
    trace = write_json(
        tmp_path / "trace.json",
        {
            "schema_version": 1,
            "project_id": "alpha-project",
            "specification_record_id": "SPEC-1",
            "change_id": "057-work-management-automation",
            "branch": "change/057-work-management-automation",
            "worktree": ".work/worktrees/057-work-management-automation",
            "pull_requests": [],
            "verifications": [],
            "merges": [],
            "closeout": None,
            "documentation_events": [],
        },
    )

    exit_code = main(
        [
            "verify-traceability",
            "--trace",
            str(trace),
            "--stage",
            "active",
            "--revision",
            "abc1234",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["revision"] == "abc1234"
    assert payload["traceability"]["stage"] == "active"
    assert payload["traceability"]["valid"] is True
