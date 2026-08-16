from __future__ import annotations

import json
from pathlib import Path

import pytest

import kis_mcp.work_management.schema as schema_module
from kis_mcp.work_management import (
    ProjectField,
    ProjectFieldKind,
    ProjectFieldOption,
    compare_project_schema,
    load_project_schema_manifest,
    plan_project_schema_repair,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = (
    REPOSITORY_ROOT / "settings" / "work-management" / "github-project-schema.json"
)


def field(name: str, kind: ProjectFieldKind, *options: str) -> ProjectField:
    return ProjectField(
        field_id=f"field-{name.casefold().replace(' ', '-')}",
        name=name,
        kind=kind,
        options=tuple(
            ProjectFieldOption(option_id=f"option-{index}", name=value)
            for index, value in enumerate(options, start=1)
        ),
    )


def test_manifest_matches_approved_programme_shape() -> None:
    manifest = load_project_schema_manifest(SCHEMA_PATH)

    assert manifest.portfolio_id == "default"
    assert len(manifest.fields) == 25
    assert len(manifest.views) == 12
    assert manifest.field("Status").kind is ProjectFieldKind.SINGLE_SELECT
    assert manifest.field("Blocked By").kind is ProjectFieldKind.TEXT
    assert "Ready" in manifest.field("Status").options
    assert "Documentation" not in manifest.field("Status").options
    assert manifest.field("Effort").options == ("Tiny", "Small", "Medium", "Large")
    assert "Documentation" in manifest.field("Delivery Stage").options
    assert manifest.field("Complexity").options == ("Small", "Medium", "Large")
    assert manifest.field("Risk Triggers").kind is ProjectFieldKind.TEXT
    assert manifest.views[0].name == "01 Inbox"
    assert manifest.views[0].filter == "status:Inbox"
    assert manifest.views[2].name == "03 Delivery Board"
    assert manifest.views[2].vertical_group_by == ("Status",)
    assert manifest.views[7].filter == 'status:"On Hold",Deferred'
    assert manifest.views[10].filter == "delivery-stage:Documentation,Commissioning"
    assert manifest.views[-1].name == "12 Completed"
    assert manifest.views[-1].filter == "status:Done"


def test_schema_comparison_reports_field_and_view_drift_deterministically() -> None:
    manifest = load_project_schema_manifest(SCHEMA_PATH)
    observed = (
        field("Status", ProjectFieldKind.SINGLE_SELECT, "Todo", "In Progress", "Done"),
        field("Repository", ProjectFieldKind.REPOSITORY),
    )

    status = compare_project_schema(
        manifest,
        observed,
        project_id="kis-mcp",
        views_observed=None,
    )

    assert status.fields_ready is False
    assert status.views_ready is None
    assert status.ready is False
    assert "Record Type" in status.missing_fields
    assert "Status:Active" in status.missing_options
    assert "Status:Ready" in status.missing_options
    assert status.type_mismatches == ()
    assert status.unverified_views == tuple(view.name for view in manifest.views)


def test_schema_comparison_accepts_complete_fields_but_keeps_unobservable_views_explicit() -> (
    None
):
    manifest = load_project_schema_manifest(SCHEMA_PATH)
    observed = tuple(
        ProjectField(
            field_id=f"observed-{index}",
            name=expected.name,
            kind=expected.kind,
            options=tuple(
                ProjectFieldOption(option_id=f"o-{index}-{position}", name=name)
                for position, name in enumerate(expected.options, start=1)
            ),
        )
        for index, expected in enumerate(manifest.fields, start=1)
    )

    status = compare_project_schema(
        manifest,
        observed,
        project_id="kis-mcp",
        views_observed=None,
    )

    assert status.fields_ready is True
    assert status.views_ready is None
    assert status.ready is False
    assert status.missing_fields == ()
    assert status.missing_options == ()
    assert status.type_mismatches == ()


def test_manifest_accepts_executable_view_semantics(tmp_path: Path) -> None:
    path = tmp_path / "schema.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "portfolio_id": "default",
                "fields": [],
                "views": [
                    {
                        "name": "01 Inbox",
                        "purpose": "Untriaged ideas and tasks",
                        "layout": "table",
                        "filter": "status:Inbox",
                        "visible_fields": ["Title", "Status", "Record Type"],
                        "sort_by": [["Priority", "asc"]],
                        "group_by": [],
                        "vertical_group_by": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    manifest = load_project_schema_manifest(path)

    view = manifest.views[0]
    assert view.filter == "status:Inbox"
    assert view.visible_fields == ("Title", "Status", "Record Type")
    assert view.sort_by == (("Priority", "asc"),)
    assert view.group_by == ()
    assert view.vertical_group_by == ()


def test_schema_comparison_rejects_view_semantic_drift() -> None:
    observation_type = getattr(schema_module, "ProjectViewObservation")
    manifest = schema_module.ProjectSchemaManifest(
        portfolio_id="default",
        fields=(),
        views=(
            schema_module.ProjectViewSpec(
                "01 Inbox",
                "Untriaged ideas and tasks",
                filter="status:Inbox",
                visible_fields=("Title", "Status"),
            ),
        ),
    )
    observed = (
        observation_type(
            name="01 Inbox",
            layout="table",
            filter="",
            visible_fields=("Title", "Status"),
        ),
    )

    status = compare_project_schema(
        manifest,
        (),
        project_id="kis-mcp",
        views_observed=observed,
    )

    assert status.views_ready is False
    assert status.ready is False
    assert status.unverified_views == ()
    assert status.view_mismatches == ("01 Inbox:filter",)
    plan = plan_project_schema_repair(status, manifest)
    assert [(action.kind, action.target) for action in plan.actions] == [
        ("update_view", "01 Inbox:filter")
    ]


@pytest.mark.parametrize("behavior_verified", [0, 1])
def test_view_observation_rejects_integer_behavior_flags(behavior_verified: int) -> None:
    with pytest.raises(ValueError, match="behavior_verified"):
        schema_module.ProjectViewObservation(
            name="01 Inbox",
            layout="table",
            filter="status:Inbox",
            behavior_verified=behavior_verified,
        )


def test_schema_comparison_rejects_unverified_saved_view_behavior() -> None:
    manifest = schema_module.ProjectSchemaManifest(
        portfolio_id="default",
        fields=(),
        views=(schema_module.ProjectViewSpec("01 Inbox", "Inbox", filter="status:Inbox"),),
    )
    observed = (
        schema_module.ProjectViewObservation(
            name="01 Inbox",
            layout="table",
            filter="status:Inbox",
            behavior_verified=False,
            behavior_mismatches=("Status:Todo",),
        ),
    )

    status = compare_project_schema(manifest, (), project_id="kis-mcp", views_observed=observed)
    plan = plan_project_schema_repair(status, manifest)

    assert status.views_ready is False
    assert status.unverified_views == ()
    assert status.view_mismatches == ("01 Inbox:behavior",)
    assert [(action.kind, action.target, action.disposition) for action in plan.actions] == [
        ("update_view", "01 Inbox:behavior", "provider_gap")
    ]


def test_name_only_view_observation_is_unverified_but_not_missing() -> None:
    manifest = schema_module.ProjectSchemaManifest(
        portfolio_id="default",
        fields=(),
        views=(schema_module.ProjectViewSpec("01 Inbox", "Inbox", filter="status:Inbox"),),
    )

    status = compare_project_schema(
        manifest,
        (),
        project_id="kis-mcp",
        views_observed=("01 Inbox",),
    )
    plan = plan_project_schema_repair(status, manifest)

    assert status.views_ready is False
    assert status.unverified_views == ("01 Inbox",)
    assert status.missing_views == ()
    assert not any(action.kind == "create_view" for action in plan.actions)


def test_schema_plan_marks_unsupported_view_semantics_manual() -> None:
    manifest = schema_module.ProjectSchemaManifest(
        portfolio_id="default",
        fields=(),
        views=(
            schema_module.ProjectViewSpec(
                "03 Delivery Board",
                "Delivery board",
                layout="board",
                vertical_group_by=("Status",),
            ),
        ),
    )
    observed = (
        schema_module.ProjectViewObservation(
            name="03 Delivery Board",
            layout="board",
            vertical_group_by=(),
        ),
    )

    status = compare_project_schema(manifest, (), project_id="kis-mcp", views_observed=observed)
    plan = plan_project_schema_repair(status, manifest)

    assert [(action.kind, action.target, action.disposition) for action in plan.actions] == [
        ("update_view", "03 Delivery Board:vertical_group_by", "manual")
    ]
