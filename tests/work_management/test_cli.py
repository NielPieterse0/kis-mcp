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


def test_schema_manifest_command_validates_repository_contract(
    tmp_path: Path, capsys
) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    manifest = (
        repository_root / "settings" / "work-management" / "github-project-schema.json"
    )

    exit_code = main(
        [
            "schema-manifest",
            "--manifest",
            str(manifest),
            "--revision",
            "abc1234",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["schema"]["portfolio_id"] == "default"
    assert len(payload["schema"]["fields"]) == 29
    assert payload["schema"]["fields"][6]["name"] == "Blocked By"
    assert [field["name"] for field in payload["schema"]["fields"]][8:10] == [
        "Complexity",
        "Risk Triggers",
    ]
    assert len(payload["schema"]["views"]) == 12


def test_merge_readiness_cli_blocks_unfinished_documentation(
    tmp_path: Path, capsys
) -> None:
    head = "a" * 40
    record_path = write_json(
        tmp_path / "record.json",
        {
            "record_id": "SPEC-110",
            "project_id": "kis-mcp",
            "title": "Slice 1",
            "record_type": "specification_slice",
            "state": "verification",
            "documentation_mode": "required",
            "documentation_impact": "planned",
            "traceability_required": True,
        },
    )
    trace_path = write_json(
        tmp_path / "trace-merge-ready.json",
        {
            "project_id": "kis-mcp",
            "specification_record_id": "SPEC-110",
            "change_id": "110-work-management-documentation-completion",
            "branch": "change/110-work-management-documentation-completion",
            "worktree": ".work/worktrees/110-work-management-documentation-completion",
            "pull_requests": [
                {
                    "repository": "NielPieterse0/kis-mcp",
                    "number": 140,
                    "head_branch": "change/110-work-management-documentation-completion",
                    "head_revision": head,
                    "base_branch": "main",
                    "state": "open",
                }
            ],
            "verifications": [
                {
                    "evidence_id": "verify-110",
                    "pull_request_number": 140,
                    "revision": head,
                    "status": "passed",
                    "command": "verify",
                    "source": "github_actions",
                    "reference": "run-110",
                }
            ],
            "merges": [],
            "closeout": None,
            "documentation_events": [],
        },
    )

    exit_code = main(
        [
            "merge-readiness",
            "--record",
            str(record_path),
            "--trace",
            str(trace_path),
            "--pull-request-number",
            "140",
            "--revision",
            "abc1234",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 4
    assert payload["ok"] is False
    assert payload["readiness"]["blocking_reasons"] == [
        "documentation_pre_merge_incomplete"
    ]
