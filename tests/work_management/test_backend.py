from __future__ import annotations

from typing import Any

import pytest

from kis_mcp.work_management import (
    ProjectBinding,
    ProjectField,
    ProjectFieldKind,
    ProjectFieldOption,
    ProjectFieldValue,
    ProjectInventory,
    ProjectInventoryBackend,
    ProjectItem,
    ProjectItemKind,
    ProjectOwnerType,
)


def binding() -> ProjectBinding:
    return ProjectBinding(
        binding_id=" github-default ",
        managed_project_id=" alpha-project ",
        provider_id=" github-mcp ",
        owner=" ExampleOwner ",
        owner_type=ProjectOwnerType.USER,
        project_number=12,
        repository="ExampleOwner/alpha",
    )


def test_project_binding_keeps_project_and_backend_identity_distinct() -> None:
    value = binding()

    assert value.binding_id == "github-default"
    assert value.managed_project_id == "alpha-project"
    assert value.provider_id == "github-mcp"
    assert value.owner == "ExampleOwner"
    assert value.repository == "ExampleOwner/alpha"
    assert value.to_json_dict()["owner_type"] == "user"


def test_project_binding_rejects_invalid_project_number() -> None:
    with pytest.raises(ValueError, match="project_number"):
        ProjectBinding(
            binding_id="github-default",
            managed_project_id="alpha-project",
            provider_id="github-mcp",
            owner="owner",
            owner_type=ProjectOwnerType.USER,
            project_number=0,
        )


def test_project_field_normalizes_unique_options() -> None:
    field = ProjectField(
        field_id="field-status",
        name="Status",
        kind=ProjectFieldKind.SINGLE_SELECT,
        options=(
            ProjectFieldOption(option_id="opt-active", name="Active"),
            ProjectFieldOption(option_id="opt-done", name="Done"),
        ),
    )

    assert [item.name for item in field.options] == ["Active", "Done"]
    assert field.to_json_dict()["kind"] == "single_select"


def test_non_select_field_rejects_options() -> None:
    with pytest.raises(ValueError, match="options"):
        ProjectField(
            field_id="field-title",
            name="Title",
            kind=ProjectFieldKind.TEXT,
            options=(ProjectFieldOption(option_id="opt-one", name="One"),),
        )


def test_project_item_is_immutable_and_json_safe() -> None:
    item = ProjectItem(
        item_id="item-42",
        kind=ProjectItemKind.ISSUE,
        title="Implement inventory",
        repository="owner/repo",
        number=42,
        state="OPEN",
        field_values=(
            ProjectFieldValue(field_name="Priority", value="High"),
            ProjectFieldValue(field_name="Estimate", value=3),
        ),
    )

    assert [value.field_name for value in item.field_values] == ["Estimate", "Priority"]
    assert item.to_json_dict()["kind"] == "issue"
    assert item.to_json_dict()["field_values"][0]["value"] == 3


def test_inventory_rejects_duplicate_fields_and_items() -> None:
    field = ProjectField(
        field_id="field-status",
        name="Status",
        kind=ProjectFieldKind.SINGLE_SELECT,
    )
    item = ProjectItem(
        item_id="item-1",
        kind=ProjectItemKind.DRAFT,
        title="Draft",
    )

    with pytest.raises(ValueError, match="field IDs"):
        ProjectInventory(
            binding=binding(),
            title="Programme",
            fields=(field, field),
        )

    with pytest.raises(ValueError, match="item IDs"):
        ProjectInventory(
            binding=binding(),
            title="Programme",
            items=(item, item),
        )


def test_inventory_exposes_truncation_and_cursor() -> None:
    inventory = ProjectInventory(
        binding=binding(),
        title="Programme",
        items=(
            ProjectItem(
                item_id="item-1",
                kind=ProjectItemKind.DRAFT,
                title="Draft",
            ),
        ),
        truncated=True,
        next_cursor="cursor-2",
    )

    document = inventory.to_json_dict()
    assert document["truncated"] is True
    assert document["next_cursor"] == "cursor-2"


def test_backend_protocol_is_async_and_provider_neutral() -> None:
    class Backend:
        async def read_inventory(
            self,
            project_binding: ProjectBinding,
            *,
            field_names: tuple[str, ...] = (),
            item_limit: int = 100,
        ) -> ProjectInventory:
            del field_names, item_limit
            return ProjectInventory(binding=project_binding, title="Programme")

    assert isinstance(Backend(), ProjectInventoryBackend)
