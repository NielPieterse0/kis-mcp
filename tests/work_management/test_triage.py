from __future__ import annotations

from kis_mcp.work_management import (
    ProjectFieldValue,
    ProjectItem,
    ProjectItemKind,
)
from kis_mcp.work_management.command_settings import load_command_plane_settings
from kis_mcp.work_management.triage import evaluate_triage


def item(**overrides: object) -> ProjectItem:
    fields = {
        "Status": "Triage",
        "Record Type": "Task",
        "Priority": "High",
        "Effort": "Small",
        "Documentation Impact": "Planned",
        "Blocked By": None,
        **overrides,
    }
    return ProjectItem(
        item_id="item-543",
        kind=ProjectItemKind.ISSUE,
        title="Triage candidate",
        repository="owner/repo",
        number=543,
        state="OPEN",
        revision="rev-1",
        field_values=tuple(
            ProjectFieldValue(field_name=name, value=value)
            for name, value in fields.items()
        ),
    )


def test_triage_requires_sections_and_project_readiness_inputs() -> None:
    result = evaluate_triage(
        item(**{"Documentation Impact": None}),
        "## Outcome\nDefined",
        load_command_plane_settings(),
    )

    assert result.ready is False
    assert result.attention_reasons == (
        "missing_issue_section:Acceptance criteria",
        "missing_required:Documentation Impact",
    )


def test_triage_fingerprint_is_stable_and_changes_with_relevant_input() -> None:
    settings = load_command_plane_settings()
    body = "## Outcome\nDefined\n\n## Acceptance criteria\nVerified"
    first = evaluate_triage(item(), body, settings)
    same = evaluate_triage(item(), body, settings)
    changed = evaluate_triage(item(Priority="Critical"), body, settings)

    assert first.ready is True
    assert first.fingerprint == same.fingerprint
    assert first.fingerprint != changed.fingerprint


def test_triage_requires_conditional_finding_semantics() -> None:
    result = evaluate_triage(
        item(**{"Record Type": "Finding"}),
        "## Outcome\nDefined\n\n## Acceptance criteria\nVerified",
        load_command_plane_settings(),
    )

    assert result.ready is False
    assert "missing_required:Severity" in result.attention_reasons
    assert "missing_required:Confidence" in result.attention_reasons


def test_triage_rejects_invalid_canonical_vocabulary() -> None:
    result = evaluate_triage(
        item(Priority="Urgent-ish"),
        "## Outcome\nDefined\n\n## Acceptance criteria\nVerified",
        load_command_plane_settings(),
    )

    assert result.ready is False
    assert result.attention_reasons == ("invalid_canonical:Priority",)
