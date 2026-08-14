from __future__ import annotations

from kis_mcp.work_management.backend import (
    ProjectBinding,
    ProjectFieldValue,
    ProjectInventory,
    ProjectItem,
    ProjectItemKind,
    ProjectOwnerType,
)
from kis_mcp.work_management.board import (
    WorkBoardProjectionBridge,
    board_field_names,
    build_work_board,
    select_current_work,
)


def _binding() -> ProjectBinding:
    return ProjectBinding(
        binding_id="github-default",
        managed_project_id="kis-mcp",
        provider_id="github-mcp",
        owner="NielPieterse0",
        owner_type=ProjectOwnerType.USER,
        project_number=1,
        repository="NielPieterse0/kis-mcp",
    )


def _item(
    number: int,
    state: str,
    *,
    owner: str | None = None,
    priority: str = "High",
    effort: str = "Small",
    change_id: str | None = None,
    title: str | None = None,
) -> ProjectItem:
    values = [
        ProjectFieldValue("Status", state),
        ProjectFieldValue("Priority", priority),
        ProjectFieldValue("Effort", effort),
        ProjectFieldValue("Created", f"2026-08-{number:02d}T00:00:00Z"),
        ProjectFieldValue("Blocked By", None),
        ProjectFieldValue("Execution Owner", owner),
        ProjectFieldValue("Record Type", "Task"),
        ProjectFieldValue("Documentation Impact", "none"),
        ProjectFieldValue("Delivery Stage", "implementing"),
        ProjectFieldValue("Verification", "pending"),
        ProjectFieldValue("Complexity", "medium"),
        ProjectFieldValue("Risk Triggers", "public_contract"),
        ProjectFieldValue("Authority Revision", f"rev-{number}"),
    ]
    if change_id is not None:
        values.append(ProjectFieldValue("Change ID", change_id))
    return ProjectItem(
        item_id=f"item-{number}",
        kind=ProjectItemKind.ISSUE,
        title=title or f"Task {number}",
        repository="NielPieterse0/kis-mcp",
        number=number,
        state="OPEN",
        url=f"https://github.com/NielPieterse0/kis-mcp/issues/{number}",
        revision=f"item-rev-{number}",
        field_values=tuple(values),
    )


def _inventory(*items: ProjectItem, truncated: bool = False) -> ProjectInventory:
    return ProjectInventory(
        binding=_binding(),
        title="KIS Work Management",
        items=tuple(items),
        truncated=truncated,
        next_cursor="cursor-2" if truncated else None,
    )


def test_board_field_names_include_queue_and_readiness_fields() -> None:
    names = board_field_names()

    assert "Status" in names
    assert "Created" in names
    assert "Blocked By" in names
    assert "Execution Owner" in names
    assert "Record Type" in names
    assert "Documentation Impact" in names


def test_board_defaults_to_active_first_and_keeps_complete_state_counts() -> None:
    snapshot = build_work_board(
        _inventory(
            _item(1, "Done", priority="Low"),
            _item(2, "Ready", priority="Critical"),
            _item(3, "Active", owner="agent-1", change_id="140-programme"),
            _item(4, "Deferred"),
        ),
        "kis-mcp",
    )

    assert [card.number for card in snapshot.cards] == [3, 2]
    assert dict(snapshot.state_counts) == {
        "active": 1,
        "deferred": 1,
        "done": 1,
        "ready": 1,
    }
    assert snapshot.next_eligible_item_id == "item-2"
    assert snapshot.complete is True
    assert snapshot.truncated is False


def test_board_can_include_history_filter_and_group() -> None:
    snapshot = build_work_board(
        _inventory(
            _item(1, "Done", owner="agent-2", title="Historical cleanup"),
            _item(2, "Active", owner="agent-1", title="Runtime generation"),
            _item(3, "Active", owner="agent-2", title="Board projection"),
        ),
        "kis-mcp",
        include_history=True,
        states=("active",),
        owner="agent-2",
        query="board",
        group_by="owner",
    )

    assert [card.number for card in snapshot.cards] == [3]
    assert dict(snapshot.groups) == {"agent-2": ("item-3",)}
    assert snapshot.states == ("active",)
    assert snapshot.owner == "agent-2"
    assert snapshot.query == "board"


def test_current_work_returns_none_without_active_claim() -> None:
    selection = select_current_work(
        _inventory(_item(1, "Ready")),
        "kis-mcp",
        "agent-1",
    )

    assert selection.status == "none"
    assert selection.selected is None
    assert selection.complete is True
    assert "project_management_take_next_work" in selection.next_actions


def test_current_work_reconstructs_exact_active_claim() -> None:
    selection = select_current_work(
        _inventory(
            _item(1, "Ready"),
            _item(2, "Active", owner="agent-1", change_id="140-programme"),
        ),
        "kis-mcp",
        "agent-1",
    )

    assert selection.status == "current"
    assert selection.complete is True
    assert selection.selected is not None
    assert selection.selected.number == 2
    assert selection.selected.change_id == "140-programme"
    assert selection.selected.execution_owner == "agent-1"
    assert selection.next_actions[:2] == (
        "inspect_change",
        "execute_change_workflow",
    )


def test_current_work_refuses_to_guess_between_multiple_claims() -> None:
    selection = select_current_work(
        _inventory(
            _item(1, "Active", owner="agent-1"),
            _item(2, "Active", owner="agent-1"),
        ),
        "kis-mcp",
        "agent-1",
    )

    assert selection.status == "ambiguous"
    assert selection.selected is None
    assert [card.number for card in selection.candidates] == [1, 2]
    assert selection.reasons == ("multiple_active_claims",)


def test_current_work_treats_truncated_inventory_as_incomplete() -> None:
    selection = select_current_work(
        _inventory(
            _item(1, "Active", owner="agent-1"),
            truncated=True,
        ),
        "kis-mcp",
        "agent-1",
    )

    assert selection.status == "incomplete"
    assert selection.complete is False
    assert selection.selected is None
    assert selection.reasons == ("inventory_truncated",)


def test_projection_bridge_is_ephemeral_and_reuses_exact_snapshot() -> None:
    bridge = WorkBoardProjectionBridge()
    assert bridge.current()["status"] == "unavailable"

    snapshot = build_work_board(
        _inventory(_item(2, "Active", owner="agent-1")),
        "kis-mcp",
    )
    bridge.publish(snapshot)

    current = bridge.current()
    assert current["status"] == "available"
    assert current["observed_at"] == snapshot.observed_at
    assert current["cards"] == [card.to_json_dict() for card in snapshot.cards]
