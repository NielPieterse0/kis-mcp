from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from kis_mcp.work_management.backend import (
    ProjectBinding,
    ProjectField,
    ProjectFieldKind,
    ProjectFieldOption,
    ProjectInventory,
    ProjectOwnerType,
)
from kis_mcp.work_management.contracts import ManagedProject
from kis_mcp.work_management.reconciliation import ReconciliationAction, ReconciliationOutcome
from kis_mcp.workflows.project_management.admission import admit_work, load_admission_contract


@dataclass
class _Settings:
    managed_projects: tuple[ManagedProject, ...]


def _project(project_id: str, repository: str) -> ManagedProject:
    return ManagedProject(
        project_id=project_id,
        local_root=f"C:\\Projects\\{project_id}",
        repository=repository,
        backend_binding="github-default",
    )


def _inventory(project_id: str, repository: str) -> ProjectInventory:
    options = lambda *names: tuple(
        ProjectFieldOption(f"opt-{index}", name)
        for index, name in enumerate(names, start=1)
    )
    fields = (
        ProjectField("f-project", "Project ID", ProjectFieldKind.TEXT),
        ProjectField("f-number", "Issue Number", ProjectFieldKind.NUMBER),
        ProjectField("f-status", "Status", ProjectFieldKind.SINGLE_SELECT, options("Inbox", "Ready", "Done")),
        ProjectField("f-type", "Record Type", ProjectFieldKind.SINGLE_SELECT, options("Idea", "Task", "Specification Slice", "Defect", "Security Finding", "Research")),
        ProjectField("f-priority", "Priority", ProjectFieldKind.SINGLE_SELECT, options("Critical", "High", "Medium", "Low")),
        ProjectField("f-effort", "Effort", ProjectFieldKind.SINGLE_SELECT, options("Tiny", "Small", "Medium", "Large")),
        ProjectField("f-doc", "Documentation Impact", ProjectFieldKind.SINGLE_SELECT, options("None", "Planned", "In Progress", "Pre Merge Complete", "Post Merge Complete", "Not Assessed")),
    )
    return ProjectInventory(
        binding=ProjectBinding(
            binding_id="github-default",
            managed_project_id=project_id,
            provider_id="github-mcp",
            owner=repository.split("/", 1)[0],
            owner_type=ProjectOwnerType.USER,
            project_number=1,
            repository=repository,
        ),
        title="Work",
        fields=fields,
        items=(),
    )


class _Service:
    def __init__(self) -> None:
        self.settings = _Settings(
            (_project("alpha", "Example/alpha"), _project("beta", "Example/beta"))
        )
        self.reconcile_calls: list[dict[str, object]] = []

    async def read_inventory(self, project_id: str, **_kwargs) -> ProjectInventory:
        project = next(item for item in self.settings.managed_projects if item.project_id == project_id)
        assert project.repository is not None
        return _inventory(project_id, project.repository)

    async def reconcile(self, project_id, desired, observed, **kwargs):
        self.reconcile_calls.append(
            {"project_id": project_id, "desired": desired, "observed": observed, **kwargs}
        )
        return (
            ReconciliationOutcome(
                project_id=project_id,
                record_id=desired[0].record_id,
                action=ReconciliationAction.CREATE,
                applied=bool(kwargs.get("apply")),
                success=True,
                provider_revision="rev-1",
                message="ok",
            ),
        )


class _External:
    def __init__(self, *, existing: dict[str, object] | None = None) -> None:
        self.existing = existing
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def __call__(self, operation: str, arguments: dict[str, object]):
        self.calls.append((operation, dict(arguments)))
        if operation == "github_search_issues":
            return {"items": [] if self.existing is None else [self.existing]}
        if operation == "github_issue_write":
            return {"number": 77, "state": "open", "title": arguments["title"], "body": arguments["body"]}
        raise AssertionError(operation)


def _formal_kwargs() -> dict[str, object]:
    return {
        "repository": "Example/beta",
        "title": "Implement deterministic admission",
        "record_type": "task",
        "priority": "high",
        "effort": "medium",
        "documentation_impact": "none",
        "context": "Formal work needs one deterministic intake path.",
        "acceptance": ["Inputs are validated.", "Project identity is derived."],
        "constraints": ["Do not invent semantic metadata."],
    }


def test_contract_declares_inbox_pre_work_and_done_history_guards() -> None:
    contract = load_admission_contract()
    assert contract["inbox_idea"] == {
        "pre_work": True,
        "auto_promote": False,
        "formal_issue_creation": False,
    }
    assert contract["done_history"]["immutable"] is True
    assert contract["derived_fields"]["Issue Number"] == "source_issue.number"


def test_formal_admission_fails_on_missing_semantic_inputs() -> None:
    service = _Service()
    kwargs = _formal_kwargs()
    kwargs["context"] = ""
    with pytest.raises(ValueError, match="context"):
        asyncio.run(admit_work(service, _External(), **kwargs))


def test_inbox_idea_resolves_registered_target_without_formalizing() -> None:
    service = _Service()
    external = _External()
    result = asyncio.run(
        admit_work(
            service,
            external,
            repository="Example/alpha",
            title="Possible future idea",
            record_type="idea",
        )
    )
    assert result["status"] == "pre_work"
    assert result["project_id"] == "alpha"
    assert result["repository"] == "Example/alpha"
    assert result["auto_promoted"] is False
    assert external.calls == []
    assert service.reconcile_calls == []


def test_preview_derives_project_identity_and_never_duplicates_project_metadata_in_body() -> None:
    service = _Service()
    result = asyncio.run(admit_work(service, _External(), **_formal_kwargs()))
    assert result["mode"] == "preview"
    assert result["project_id"] == "beta"
    assert result["repository"] == "Example/beta"
    body = result["source_issue"]["body"]
    assert "## Acceptance criteria" in body
    assert "Project ID:" not in body
    assert "Priority:" not in body
    assert result["project_fields"]["Project ID"] == "beta"
    assert result["project_fields"]["Issue Number"] is None


def test_follow_on_body_records_lineage_without_reopening_history() -> None:
    kwargs = _formal_kwargs()
    kwargs["lineage_issue_number"] = 42
    result = asyncio.run(admit_work(_Service(), _External(), **kwargs))
    assert "Follow-on to #42." in result["source_issue"]["body"]


def test_apply_creates_source_issue_then_projects_canonical_source_identity() -> None:
    service = _Service()
    external = _External()
    result = asyncio.run(
        admit_work(
            service,
            external,
            **_formal_kwargs(),
            apply=True,
            idempotency_key="agent-a-542-create",
        )
    )
    assert result["mode"] == "apply"
    assert result["source_issue"]["number"] == 77
    assert [name for name, _args in external.calls] == [
        "github_search_issues",
        "github_issue_write",
    ]
    call = service.reconcile_calls[0]
    desired = call["desired"][0]
    assert desired.project_id == "beta"
    assert desired.source_repository == "Example/beta"
    assert desired.source_number == 77
    assert dict(desired.fields)["Project ID"] == "beta"
    assert dict(desired.fields)["Issue Number"] == 77
    assert call["idempotency_key"] == "agent-a-542-create:project"


def test_apply_reuses_open_idempotency_match_without_creating_duplicate_issue() -> None:
    service = _Service()
    external = _External(existing={"number": 77, "state": "open", "title": "existing"})
    result = asyncio.run(
        admit_work(
            service,
            external,
            **_formal_kwargs(),
            apply=True,
            idempotency_key="agent-a-542-create",
        )
    )
    assert result["source_issue"]["number"] == 77
    assert [name for name, _args in external.calls] == ["github_search_issues"]


def test_closed_idempotency_match_is_immutable_and_never_reopened() -> None:
    service = _Service()
    external = _External(existing={"number": 77, "state": "closed", "title": "done"})
    result = asyncio.run(
        admit_work(
            service,
            external,
            **_formal_kwargs(),
            apply=True,
            idempotency_key="agent-a-542-create",
        )
    )
    assert result["status"] == "immutable_history"
    assert result["source_issue"]["number"] == 77
    assert result["next_action"] == "create_follow_on_with_new_idempotency_key_and_lineage"
    assert [name for name, _args in external.calls] == ["github_search_issues"]
    assert service.reconcile_calls == []


def test_unknown_or_ambiguous_repository_identity_fails_closed() -> None:
    service = _Service()
    kwargs = _formal_kwargs()
    kwargs["repository"] = "Example/missing"
    with pytest.raises(ValueError, match="registered repository"):
        asyncio.run(admit_work(service, _External(), **kwargs))


def test_checked_in_admission_contract_matches_json_schema() -> None:
    import json
    from pathlib import Path

    from jsonschema import Draft202012Validator

    root = Path(__file__).resolve().parents[3]
    contract = json.loads(
        (root / "settings" / "work-management" / "contracts" / "work-admission-conformance.json").read_text(encoding="utf-8")
    )
    schema = json.loads(
        (root / "contracts" / "work-management" / "work-admission-conformance.schema.json").read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(schema).iter_errors(contract)) == []
