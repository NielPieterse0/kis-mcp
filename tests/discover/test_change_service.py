from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.discover.change_contracts import (
    ChangePathRecord,
    ChangeSummary,
    LocalChangeInventory,
)
from kis_mcp.discover.change_inspection_contracts import (
    ChangeIdentity,
    ChangeImpactSummary,
    ChangedFile,
    ChangeUnknown,
    InspectChangeRequest,
    InspectChangeResponse,
)
from kis_mcp.discover.change_service import InspectChangeService
from kis_mcp.discover.read_authority import ReadAuthority


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = (
    REPOSITORY_ROOT
    / "contracts"
    / "discover"
    / "inspect-change-working-tree-response.schema.json"
)


class _StubReader:
    def __init__(self, inventory: LocalChangeInventory) -> None:
        self.inventory = inventory
        self.calls: list[str] = []

    def inspect_local_changes(self, project_path: str) -> LocalChangeInventory:
        self.calls.append(project_path)
        return self.inventory


def _inventory(*, truncated: bool = False) -> LocalChangeInventory:
    diagnostics = (
        {
            "code": "GIT_CHANGE_OUTPUT_TRUNCATED",
            "message": "Local Git change output exceeded the configured byte limit.",
        },
    ) if truncated else ()
    return LocalChangeInventory(
        project_path=r"C:\Projects\example",
        repository_root=r"C:\Projects\example",
        changes=(
            ChangePathRecord(
                path="src/new.py",
                previous_path="legacy/old.py",
                staged_status="renamed",
                worktree_status="modified",
            ),
            ChangePathRecord(path="tests/test_new.py", untracked=True),
            ChangePathRecord(path="contracts/api.schema.json", staged_status="modified"),
            ChangePathRecord(path="docs/guide.md", worktree_status="modified"),
            ChangePathRecord(path="settings/app.json", staged_status="modified"),
            ChangePathRecord(path="policy/rules.json", staged_status="modified"),
            ChangePathRecord(path="NOTICE", staged_status="modified"),
        ),
        summary=ChangeSummary(total=7, staged=5, unstaged=2, untracked=1, renamed=1),
        diagnostics=diagnostics,
        truncated=truncated,
    )


def test_request_accepts_only_working_tree_source() -> None:
    request = InspectChangeRequest(path=r"C:\Projects\example")

    assert request.path == r"C:\Projects\example"
    assert request.source == "working_tree"

    with pytest.raises(ValueError, match="non-empty"):
        InspectChangeRequest(path="  ")
    with pytest.raises(ValueError, match="working_tree"):
        InspectChangeRequest(path=r"C:\Projects\example", source="commit")


def test_response_serializes_exact_versioned_contract() -> None:
    response = InspectChangeResponse(
        available=True,
        project_path=r"C:\Projects\example",
        repository_root=r"C:\Projects\example",
        change=ChangeIdentity(source="working_tree", fingerprint="a" * 64),
        changed_files=(
            ChangedFile(
                path="src/new.py",
                previous_path="legacy/old.py",
                staged_status="renamed",
                worktree_status="modified",
                untracked=False,
                categories=("source",),
            ),
        ),
        affected_scopes=("legacy", "src"),
        changed_tests=(),
        contract_paths=(),
        documentation_paths=(),
        configuration_paths=(),
        policy_paths=(),
        impact_summary=ChangeImpactSummary(
            total_files=1,
            source_files=1,
            test_files=0,
            contract_files=0,
            documentation_files=0,
            configuration_files=0,
            policy_files=0,
            other_files=0,
        ),
        diagnostics=(),
        unknowns=(
            ChangeUnknown(
                code="CHANGE_SYMBOL_IMPACT_UNAVAILABLE",
                reason="Symbol impact is not available in this slice.",
            ),
        ),
        confidence="high",
        truncated=False,
    )

    assert response.to_json_dict() == {
        "schema_version": 1,
        "tool": "inspect_change",
        "source": "working_tree",
        "available": True,
        "project_path": r"C:\Projects\example",
        "repository_root": r"C:\Projects\example",
        "change": {"source": "working_tree", "fingerprint": "a" * 64},
        "changed_files": [
            {
                "path": "src/new.py",
                "previous_path": "legacy/old.py",
                "staged_status": "renamed",
                "worktree_status": "modified",
                "untracked": False,
                "categories": ["source"],
            }
        ],
        "affected_scopes": ["legacy", "src"],
        "changed_tests": [],
        "contract_paths": [],
        "documentation_paths": [],
        "configuration_paths": [],
        "policy_paths": [],
        "impact_summary": {
            "total_files": 1,
            "source_files": 1,
            "test_files": 0,
            "contract_files": 0,
            "documentation_files": 0,
            "configuration_files": 0,
            "policy_files": 0,
            "other_files": 0,
        },
        "diagnostics": [],
        "unknowns": [
            {
                "code": "CHANGE_SYMBOL_IMPACT_UNAVAILABLE",
                "reason": "Symbol impact is not available in this slice.",
            }
        ],
        "confidence": "high",
        "truncated": False,
    }


def test_representative_response_matches_checked_in_schema() -> None:
    response = InspectChangeService(_StubReader(_inventory())).inspect(
        InspectChangeRequest(path=r"C:\Projects\example")
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(response.to_json_dict()),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )

    assert errors == []


def test_service_projects_inventory_into_deterministic_impact() -> None:
    reader = _StubReader(_inventory())
    service = InspectChangeService(reader)

    first = service.inspect(InspectChangeRequest(path=r"C:\Projects\example"))
    second = service.inspect(InspectChangeRequest(path=r"C:\Projects\example"))

    assert reader.calls == [r"C:\Projects\example", r"C:\Projects\example"]
    assert first == second
    assert first.available is True
    assert first.repository_root == r"C:\Projects\example"
    assert len(first.change.fingerprint) == 64
    assert [item.path for item in first.changed_files] == [
        "src/new.py",
        "tests/test_new.py",
        "contracts/api.schema.json",
        "docs/guide.md",
        "settings/app.json",
        "policy/rules.json",
        "NOTICE",
    ]
    assert [item.categories for item in first.changed_files] == [
        ("source",),
        ("test",),
        ("contract",),
        ("documentation",),
        ("configuration",),
        ("policy",),
        ("other",),
    ]
    assert first.affected_scopes == (
        "contracts",
        "docs",
        "legacy",
        "policy",
        "settings",
        "src",
        "tests",
        ".",
    )
    assert first.changed_tests == ("tests/test_new.py",)
    assert first.contract_paths == ("contracts/api.schema.json",)
    assert first.documentation_paths == ("docs/guide.md",)
    assert first.configuration_paths == ("settings/app.json",)
    assert first.policy_paths == ("policy/rules.json",)
    assert first.impact_summary == ChangeImpactSummary(
        total_files=7,
        source_files=1,
        test_files=1,
        contract_files=1,
        documentation_files=1,
        configuration_files=1,
        policy_files=1,
        other_files=1,
    )
    assert [item.code for item in first.unknowns] == [
        "CHANGE_DEPENDANT_IMPACT_UNAVAILABLE",
        "CHANGE_SYMBOL_IMPACT_UNAVAILABLE",
        "CHANGE_VERIFICATION_MAPPING_UNAVAILABLE",
    ]
    assert first.confidence == "high"
    assert first.truncated is False


def test_fingerprint_changes_when_retained_inventory_changes() -> None:
    original = InspectChangeService(_StubReader(_inventory())).inspect(
        InspectChangeRequest(path=r"C:\Projects\example")
    )
    changed_inventory = LocalChangeInventory(
        project_path=r"C:\Projects\example",
        repository_root=r"C:\Projects\example",
        changes=(ChangePathRecord(path="different.txt", untracked=True),),
        summary=ChangeSummary(total=1, untracked=1),
    )
    changed = InspectChangeService(_StubReader(changed_inventory)).inspect(
        InspectChangeRequest(path=r"C:\Projects\example")
    )

    assert original.change.fingerprint != changed.change.fingerprint


def test_unavailable_inventory_returns_low_confidence_unknown() -> None:
    inventory = LocalChangeInventory(
        project_path=r"C:\Projects\example",
        repository_root=None,
        diagnostics=(
            {
                "code": "GIT_NOT_REPOSITORY",
                "message": "No local Git repository metadata was found.",
            },
        ),
    )

    response = InspectChangeService(_StubReader(inventory)).inspect(
        InspectChangeRequest(path=r"C:\Projects\example")
    )

    assert response.available is False
    assert response.changed_files == ()
    assert response.affected_scopes == ()
    assert response.diagnostics == inventory.diagnostics
    assert [item.code for item in response.unknowns] == [
        "CHANGE_REPOSITORY_EVIDENCE_UNAVAILABLE"
    ]
    assert response.confidence == "low"
    assert response.truncated is False


def test_truncated_inventory_preserves_diagnostics_and_medium_confidence() -> None:
    inventory = _inventory(truncated=True)

    response = InspectChangeService(_StubReader(inventory)).inspect(
        InspectChangeRequest(path=r"C:\Projects\example")
    )

    assert response.available is True
    assert response.diagnostics == inventory.diagnostics
    assert response.confidence == "medium"
    assert response.truncated is True


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        },
    )


def test_service_composes_with_real_git_reader(
    project_root: Path,
    discover_settings,
) -> None:
    _git(project_root, "init", "-b", "main")
    _git(project_root, "config", "user.name", "Discover Tests")
    _git(project_root, "config", "user.email", "discover@example.invalid")
    tracked = project_root / "src" / "tracked.py"
    tracked.parent.mkdir(parents=True)
    tracked.write_text("value = 1\n", encoding="utf-8")
    _git(project_root, "add", "--", "src/tracked.py")
    _git(project_root, "commit", "-m", "initial")

    tracked.write_text("value = 2\n", encoding="utf-8")
    staged = project_root / "tests" / "test_new.py"
    staged.parent.mkdir(parents=True)
    staged.write_text("def test_new():\n    assert True\n", encoding="utf-8")
    _git(project_root, "add", "--", "tests/test_new.py")
    (project_root / "README.md").write_text("changed\n", encoding="utf-8")

    from kis_mcp.discover.git_reader import GitReader

    reader = GitReader(
        authority=ReadAuthority(Path(r"C:\Projects"), discover_settings),
        settings=discover_settings,
    )
    response = InspectChangeService(reader).inspect(
        InspectChangeRequest(path=str(project_root))
    )

    assert response.available is True
    assert [item.path for item in response.changed_files] == [
        "README.md",
        "src/tracked.py",
        "tests/test_new.py",
    ]
    assert [item.categories for item in response.changed_files] == [
        ("documentation",),
        ("source",),
        ("test",),
    ]
    assert response.changed_tests == ("tests/test_new.py",)
    assert response.confidence == "high"


def test_failed_change_read_is_unavailable_even_with_repository_root() -> None:
    inventory = LocalChangeInventory(
        project_path=r"C:\Projects\example",
        repository_root=r"C:\Projects\example",
        diagnostics=(
            {
                "code": "GIT_CHANGE_READ_FAILED",
                "message": "Local Git change evidence could not be read safely.",
            },
        ),
    )

    response = InspectChangeService(_StubReader(inventory)).inspect(
        InspectChangeRequest(path=r"C:\Projects\example")
    )

    assert response.available is False
    assert [item.code for item in response.unknowns] == [
        "CHANGE_REPOSITORY_EVIDENCE_UNAVAILABLE"
    ]
    assert response.confidence == "low"


def test_non_fatal_diagnostic_keeps_repository_evidence_available() -> None:
    inventory = LocalChangeInventory(
        project_path=r"C:\Projects\example",
        repository_root=r"C:\Projects\example",
        diagnostics=(
            {
                "code": "CHANGE_CLASSIFICATION_PARTIAL",
                "message": "One changed path could not be classified precisely.",
            },
        ),
    )

    response = InspectChangeService(_StubReader(inventory)).inspect(
        InspectChangeRequest(path=r"C:\Projects\example")
    )

    assert response.available is True
    assert response.confidence == "medium"
