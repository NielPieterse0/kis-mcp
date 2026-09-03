from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Awaitable, Callable

from kis_mcp.work_management.reconciliation import DesiredProjection

ExternalInvoker = Callable[[str, dict[str, object]], Awaitable[dict[str, Any]]]


def _contract_path() -> Path:
    return (
        Path(__file__).resolve().parents[4]
        / "settings"
        / "work-management"
        / "contracts"
        / "work-admission-conformance.json"
    )


def load_admission_contract(path: Path | None = None) -> dict[str, Any]:
    target = path or _contract_path()
    document = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("work admission conformance contract is invalid")
    return document


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _resolve_project(service: Any, repository: str) -> Any:
    target = _text(repository, "repository").casefold()
    matches = [
        project
        for project in service.settings.managed_projects
        if isinstance(project.repository, str)
        and project.repository.casefold() == target
    ]
    if len(matches) != 1:
        raise ValueError("registered repository identity must resolve uniquely")
    return matches[0]


def _body(
    context: str,
    acceptance: tuple[str, ...],
    constraints: tuple[str, ...],
    lineage_issue_number: int | None,
) -> str:
    lines = ["## Context", "", context, "", "## Acceptance criteria", ""]
    lines.extend(f"- {item}" for item in acceptance)
    lines.extend(["", "## Constraints", ""])
    lines.extend(f"- {item}" for item in constraints)
    if lineage_issue_number is not None:
        lines.extend(["", f"Follow-on to #{lineage_issue_number}."])
    return "\n".join(lines).strip() + "\n"


def _items(values: object, label: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError(f"{label} must contain at least one item")
    normalized = tuple(_text(value, label) for value in values)
    return normalized


def _record_id(record_type: str, issue_number: int | None) -> str:
    prefixes = {
        "idea": "IDEA",
        "task": "TASK",
        "specification_slice": "SPEC",
        "defect": "BUG",
        "security_finding": "SEC",
        "research": "RES",
    }
    prefix = prefixes.get(record_type)
    if prefix is None:
        raise ValueError("record_type is not supported by formal admission")
    return f"{prefix}-{issue_number or 1}"


def _search_query(repository: str, idempotency_key: str) -> str:
    owner, repo = repository.split("/", 1)
    marker = f"kis-admission:{idempotency_key}"
    return f'repo:{owner}/{repo} in:body "{marker}"'


def _source_body(body: str, idempotency_key: str) -> str:
    return body + f"\n<!-- kis-admission:{idempotency_key} -->\n"


async def admit_work(
    service: Any,
    external: ExternalInvoker,
    *,
    repository: str,
    title: str,
    record_type: str,
    priority: str | None = None,
    effort: str | None = None,
    documentation_impact: str | None = None,
    context: str | None = None,
    acceptance: list[str] | tuple[str, ...] | None = None,
    constraints: list[str] | tuple[str, ...] | None = None,
    lineage_issue_number: int | None = None,
    apply: bool = False,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    project = _resolve_project(service, repository)
    normalized_type = _text(record_type, "record_type").casefold()
    normalized_title = _text(title, "title")
    if normalized_type == "idea":
        return {
            "status": "pre_work",
            "project_id": project.project_id,
            "repository": project.repository,
            "auto_promoted": False,
        }

    normalized_context = _text(context, "context")
    normalized_acceptance = _items(acceptance, "acceptance")
    normalized_constraints = _items(constraints, "constraints")
    normalized_priority = _text(priority, "priority").casefold()
    normalized_effort = _text(effort, "effort").casefold()
    normalized_docs = _text(documentation_impact, "documentation_impact").casefold()
    source_body = _body(
        normalized_context,
        normalized_acceptance,
        normalized_constraints,
        lineage_issue_number,
    )
    fields: dict[str, object] = {
        "Project ID": project.project_id,
        "Issue Number": None,
        "Record Type": normalized_type.replace("_", " ").title(),
        "Priority": normalized_priority.title(),
        "Effort": normalized_effort.title(),
        "Documentation Impact": normalized_docs.replace("_", " ").title(),
    }
    preview = {
        "mode": "preview",
        "project_id": project.project_id,
        "repository": project.repository,
        "source_issue": {"title": normalized_title, "body": source_body, "number": None},
        "project_fields": fields,
    }
    if not apply:
        return preview

    key = _text(idempotency_key, "idempotency_key")
    search = await external(
        "github_search_issues",
        {"query": _search_query(project.repository, key)},
    )
    matches = search.get("items", []) if isinstance(search, dict) else []
    if not isinstance(matches, list):
        raise ValueError("issue search returned invalid items")
    if len(matches) > 1:
        raise ValueError("idempotency search is ambiguous")
    if matches:
        issue = matches[0]
        number = issue.get("number")
        if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
            raise ValueError("idempotency match has invalid issue number")
        if str(issue.get("state", "")).casefold() == "closed":
            return {
                "mode": "apply",
                "status": "immutable_history",
                "project_id": project.project_id,
                "repository": project.repository,
                "source_issue": issue,
                "next_action": "create_follow_on_with_new_idempotency_key_and_lineage",
            }
    else:
        owner, repo = project.repository.split("/", 1)
        issue = await external(
            "github_issue_write",
            {
                "method": "create",
                "owner": owner,
                "repo": repo,
                "title": normalized_title,
                "body": _source_body(source_body, key),
            },
        )
        number = issue.get("number")

    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        raise ValueError("created or matched source issue has invalid number")
    fields["Issue Number"] = number
    desired = DesiredProjection(
        project_id=project.project_id,
        record_id=_record_id(normalized_type, number),
        fields=tuple(fields.items()),
        source_repository=project.repository,
        source_number=number,
        source_kind="issue",
    )
    inventory = await service.read_inventory(project.project_id)
    outcomes = await service.reconcile(
        project.project_id,
        (desired,),
        (),
        supported_fields=tuple(field.name for field in inventory.fields),
        apply=True,
        idempotency_key=f"{key}:project",
    )
    return {
        "mode": "apply",
        "status": "admitted",
        "project_id": project.project_id,
        "repository": project.repository,
        "source_issue": issue,
        "project_fields": fields,
        "outcomes": [item.to_json_dict() for item in outcomes],
    }


def register_project_management_admission_tool(
    server: Any,
    service: Any,
    external: ExternalInvoker,
) -> None:
    from fastmcp import FastMCP

    tool_server = FastMCP("kis-mcp-project-management-admission")

    @tool_server.tool(
        annotations={
            "read_only_hint": False,
            "destructive_hint": False,
            "idempotent_hint": True,
            "open_world_hint": True,
        }
    )
    async def project_management_admit_work(
        repository: str,
        title: str,
        record_type: str,
        priority: str | None = None,
        effort: str | None = None,
        documentation_impact: str | None = None,
        context: str | None = None,
        acceptance: list[str] | None = None,
        constraints: list[str] | None = None,
        lineage_issue_number: int | None = None,
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return await admit_work(
            service,
            external,
            repository=repository,
            title=title,
            record_type=record_type,
            priority=priority,
            effort=effort,
            documentation_impact=documentation_impact,
            context=context,
            acceptance=acceptance,
            constraints=constraints,
            lineage_issue_number=lineage_issue_number,
            apply=apply,
            idempotency_key=idempotency_key,
        )

    server.mount(tool_server)


__all__ = [
    "admit_work",
    "load_admission_contract",
    "register_project_management_admission_tool",
]
