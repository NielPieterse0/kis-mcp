from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from kis_mcp.projects import load_project_registry_settings
from kis_mcp.providers.supabase.routing import (
    SupabaseProjectRouting,
    SupabaseProjectRoutingError,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPOSITORY_ROOT / "settings" / "projects.settings.json"
PROJECT_REF = "mmxuicfrdalymczdapjq"


def _tool(name: str, *, read_only: bool) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        annotations=SimpleNamespace(readOnlyHint=read_only),
    )


def _routing() -> SupabaseProjectRouting:
    registry = load_project_registry_settings(REGISTRY_PATH, boundary="C:\\Projects")
    tools = (
        _tool("list_projects", read_only=True),
        _tool("get_project", read_only=True),
        _tool("get_project_url", read_only=True),
        _tool("apply_migration", read_only=False),
    )
    return SupabaseProjectRouting(registry, lambda: tools)


def test_registered_project_id_is_authorized_for_project_operations() -> None:
    routing = _routing()

    routing.authorize("get_project_url", {"project_id": PROJECT_REF})
    routing.authorize("apply_migration", {"project_id": PROJECT_REF})


def test_unregistered_project_id_is_rejected_before_upstream_execution() -> None:
    routing = _routing()

    with pytest.raises(SupabaseProjectRoutingError, match="not registered"):
        routing.authorize("get_project_url", {"project_id": "aaaaaaaaaaaaaaaaaaaa"})


def test_targetless_read_only_account_discovery_is_allowed() -> None:
    routing = _routing()

    routing.authorize("list_projects", {})


def test_live_get_project_id_is_recognized_only_for_registered_project() -> None:
    routing = _routing()

    assert routing.is_registered_project_read("get_project", {"id": PROJECT_REF}) is True
    assert (
        routing.is_registered_project_read(
            "get_project",
            {"id": "aaaaaaaaaaaaaaaaaaaa"},
        )
        is False
    )
    assert routing.is_registered_project_read("list_projects", {}) is False


def test_targetless_mutation_and_unknown_metadata_fail_closed() -> None:
    routing = _routing()

    with pytest.raises(SupabaseProjectRoutingError, match="registered project_id"):
        routing.authorize("apply_migration", {})
    with pytest.raises(SupabaseProjectRoutingError, match="registered project_id"):
        routing.authorize("unknown_tool", {})
