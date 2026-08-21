from __future__ import annotations

import json
import shlex
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
    assert len(manifest.fields) == 28
    assert len(manifest.views) == 12
    assert manifest.field("Status").kind is ProjectFieldKind.SINGLE_SELECT
    assert manifest.field("Blocked By").kind is ProjectFieldKind.TEXT
    assert "Ready" in manifest.field("Status").options
    assert "Documentation" not in manifest.field("Status").options
    assert manifest.field("Effort").options == ("Tiny", "Small", "Medium", "Large")
    assert "Documentation" in manifest.field("Delivery Stage").options
    assert manifest.field("Complexity").options == ("Small", "Medium", "Large")
    assert manifest.field("Risk Triggers").kind is ProjectFieldKind.TEXT
    assert tuple(field.name for field in manifest.fields[-3:]) == (
        "Live Verification",
        "Commissioning Key",
        "Live Verification Evidence",
    )
    assert manifest.field("Live Verification").options == (
        "Not Assessed", "Not Required", "Pending", "Passed", "Failed", "Blocked"
    )
    assert manifest.field("Commissioning Key").kind is ProjectFieldKind.TEXT
    assert manifest.field("Live Verification Evidence").kind is ProjectFieldKind.TEXT
    assert manifest.views[0].name == "01 Inbox"
    assert manifest.views[0].filter == "status:Inbox"
    assert manifest.views[2].name == "03 Delivery Board"
    assert manifest.views[2].vertical_group_by == ("Status",)
    assert manifest.views[7].filter == 'status:"On Hold",Deferred'
    assert manifest.views[10].filter == (
        "delivery-stage:Documentation,Commissioning "
        'status:Inbox,Triage,Proposed,Approved,Ready,Active,Blocked,"On Hold",'
        "Deferred,Rejected,Superseded,Done"
    )
    assert manifest.views[-1].name == "12 Completed"
    assert manifest.views[-1].filter == "status:Done"


def test_manifest_views_require_explicit_canonical_status_filters() -> None:
    manifest = load_project_schema_manifest(SCHEMA_PATH)
    canonical = {value.casefold() for value in manifest.field("Status").options}

    for view in manifest.views:
        status_tokens = [
            token.partition(":")[2]
            for token in shlex.split(view.filter, posix=True)
            if token.partition(":")[0].casefold() == "status"
        ]
        assert len(status_tokens) == 1, view.name
        values = {
            value.strip().casefold()
            for value in status_tokens[0].split(",")
            if value.strip()
        }
        assert values
        assert values <= canonical, view.name
        assert not {"todo", "in progress"} & values, view.name


@pytest.mark.parametrize(
    ("filter_text", "message"),
    (
        ("record-type:Task", "exactly one status qualifier"),
        ("status:Inbox status:Done", "exactly one status qualifier"),
        ("status:", "malformed status values"),
        ("status:,Inbox", "malformed status values"),
        ("status:Inbox,", "malformed status values"),
        ("status:Inbox,,Done", "malformed status values"),
        ("status:Inbox,Inbox", "duplicate status values"),
        ('status:"On Hold', "invalid canonical view filter"),
        ("status:Todo", "non-canonical status values"),
        ('status:"In Progress"', "non-canonical status values"),
    ),
)
def test_manifest_rejects_missing_or_legacy_status_filters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filter_text: str,
    message: str,
) -> None:
    document = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    document["views"][0]["filter"] = filter_text
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(schema_module, "_default_project_schema_path", lambda: path)

    with pytest.raises(ValueError, match=message):
        load_project_schema_manifest(path)


def test_canonical_manifest_requires_status_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    document["fields"] = [field for field in document["fields"] if field["name"] != "Status"]
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(schema_module, "_default_project_schema_path", lambda: path)

    with pytest.raises(ValueError, match="canonical project schema requires a Status field"):
        load_project_schema_manifest(path)


def test_canonical_manifest_requires_exactly_twelve_views(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    document["views"] = document["views"][:-1]
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(schema_module, "_default_project_schema_path", lambda: path)

    with pytest.raises(ValueError, match="canonical project schema requires exactly 12 views"):
        load_project_schema_manifest(path)


def test_explicit_alternate_twelve_view_manifest_remains_generic(tmp_path: Path) -> None:
    document = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    document["fields"] = [field for field in document["fields"] if field["name"] != "Status"]
    path = tmp_path / "alternate-schema.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    manifest = load_project_schema_manifest(path)

    assert manifest.portfolio_id == "default"
    assert len(manifest.views) == 12


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


def test_canonical_manifest_rejects_field_projection_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    priority = next(field for field in document["fields"] if field["name"] == "Priority")
    priority["options"] = ["High", "Critical", "Medium", "Low"]
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(schema_module, "_default_project_schema_path", lambda: path)

    with pytest.raises(ValueError, match="Priority options drift from canonical Work semantics"):
        load_project_schema_manifest(path)
