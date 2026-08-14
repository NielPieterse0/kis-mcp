from __future__ import annotations

from pathlib import Path

from kis_mcp.work_management import (
    ProjectField,
    ProjectFieldKind,
    ProjectFieldOption,
    compare_project_schema,
    load_project_schema_manifest,
    plan_project_schema_repair,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
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


def test_schema_repair_plan_makes_provider_gaps_explicit() -> None:
    manifest = load_project_schema_manifest(MANIFEST_PATH)
    status = compare_project_schema(
        manifest,
        (
            field(
                "Status", ProjectFieldKind.SINGLE_SELECT, "Todo", "In Progress", "Done"
            ),
            field("Repository", ProjectFieldKind.REPOSITORY),
        ),
        project_id="kis-mcp",
        views_observed=None,
    )

    plan = plan_project_schema_repair(status, manifest)

    assert plan.ready is False
    assert plan.automatic_ready is False
    assert any(
        action.target == "Effort" and action.kind == "create_field"
        for action in plan.actions
    )
    assert any(
        action.target == "Status:Ready" and action.kind == "add_option"
        for action in plan.actions
    )
    assert all(action.disposition == "provider_gap" for action in plan.actions)
    assert "01 Inbox" in plan.unverified_views
