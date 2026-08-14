from __future__ import annotations

from kis_mcp.work_management import (
    ProjectBinding,
    ProjectFieldValue,
    ProjectInventory,
    ProjectItem,
    ProjectItemKind,
    ProjectOwnerType,
    build_item_projections,
    select_next_project_item,
)


def binding() -> ProjectBinding:
    return ProjectBinding(
        binding_id="github-default",
        managed_project_id="alpha-project",
        provider_id="github-mcp",
        owner="ExampleOwner",
        owner_type=ProjectOwnerType.USER,
        project_number=1,
        repository="ExampleOwner/alpha",
    )


def item(number: int, **fields: object) -> ProjectItem:
    values = {
        "Record Type": "Task",
        "Documentation Impact": "Planned",
        **fields,
    }
    return ProjectItem(
        item_id=f"item-{number}",
        kind=ProjectItemKind.ISSUE,
        title=f"Issue {number}",
        repository="ExampleOwner/alpha",
        number=number,
        state="OPEN",
        revision=f"rev-{number}",
        field_values=tuple(
            ProjectFieldValue(field_name=name, value=value)
            for name, value in values.items()
        ),
    )


def inventory(*items: ProjectItem, truncated: bool = False) -> ProjectInventory:
    return ProjectInventory(
        binding=binding(),
        title="Programme",
        items=items,
        truncated=truncated,
        next_cursor="next" if truncated else None,
    )


def test_project_next_work_uses_ready_unclaimed_queue_and_native_blocker_when_observed() -> (
    None
):
    current = inventory(
        item(
            10,
            Status="Ready",
            Priority="Critical",
            Effort="Large",
            **{"Blocked By": None},
        ),
        item(
            11,
            Status="Ready",
            Priority="Critical",
            Effort="Tiny",
            **{"Blocked By": None},
        ),
        item(
            12,
            Status="Ready",
            Priority="Critical",
            Effort="Tiny",
            **{"Execution Owner": "kis-dev/s1", "Blocked By": None},
        ),
        item(
            13,
            Status="Ready",
            Priority="Critical",
            Effort="Tiny",
            **{"Blocked By": "#4"},
        ),
        item(
            14,
            Status="Active",
            Priority="Critical",
            Effort="Tiny",
            **{"Blocked By": None},
        ),
    )

    result = select_next_project_item(current)

    assert result.selected is not None
    assert result.selected.number == 11
    reasons = {entry.number: entry.reasons for entry in result.evaluations}
    assert reasons[12] == ("already_claimed:kis-dev/s1",)
    assert reasons[13] == ("native_dependency_blocking",)
    assert reasons[14] == ("state_not_ready",)
    assert result.dependency_evidence == "observed"


def test_project_next_work_excludes_items_when_dependency_evidence_is_unavailable() -> (
    None
):
    result = select_next_project_item(
        inventory(item(15, Status="Ready", Priority="High", Effort="Small"))
    )

    assert result.selected is None
    assert result.dependency_evidence == "unavailable"
    assert result.evaluations[0].reasons == ("dependency_evidence_unavailable",)


def test_project_next_work_refuses_partial_inventory() -> None:
    result = select_next_project_item(
        inventory(
            item(20, Status="Ready", Priority="High", Effort="Small"), truncated=True
        )
    )

    assert result.selected is None
    assert result.complete is False
    assert result.reasons == ("inventory_truncated",)


def test_item_projections_preserve_source_identity_and_revision() -> None:
    current = item(30, Status="Ready", Priority="High", Effort="Small")
    desired, observed = build_item_projections(
        "alpha-project",
        current,
        {"Execution Owner": "kis-dev/session-x"},
    )

    assert desired.record_id == "WORK-30"
    assert desired.expected_revision == "rev-30"
    assert desired.source_repository == "ExampleOwner/alpha"
    assert desired.source_number == 30
    assert observed.external_id == "item-30"
    assert observed.revision == "rev-30"
    assert dict(observed.fields)["Status"] == "Ready"
