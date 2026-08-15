from __future__ import annotations

from pathlib import Path

from kis_mcp.work_management import (
    ProjectField,
    ProjectFieldKind,
    ProjectFieldOption,
    compare_project_schema,
    load_project_schema_manifest,
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
    assert manifest.views[-1].name == "12 Completed"


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
