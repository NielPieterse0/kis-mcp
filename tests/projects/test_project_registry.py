from __future__ import annotations

from pathlib import Path

import pytest

from kis_mcp.projects import load_project_registry_settings


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPOSITORY_ROOT / "settings" / "projects.settings.json"


def test_registry_indexes_declared_provider_resources() -> None:
    registry = load_project_registry_settings(REGISTRY_PATH, boundary="C:\\Projects")

    assert registry.github_repositories == (
        "nielpieterse0/app-dev-core",
        "nielpieterse0/chatgpt-skill",
        "nielpieterse0/college",
        "nielpieterse0/commodity",
        "nielpieterse0/doc-solution",
        "nielpieterse0/gpt-os",
        "nielpieterse0/import-isolate",
        "nielpieterse0/kis-mcp",
        "nielpieterse0/mi-fi",
        "nielpieterse0/prose2llm",
        "nielpieterse0/signal",
    )
    assert registry.github_project_coordinates == (("NielPieterse0", "user", 1),)
    assert registry.supabase_project_refs == ("mmxuicfrdalymczdapjq",)
    assert registry.project_for_root("c:\\projects\\GPT-OS").project_id == "gpt-os"
    assert registry.project_for_root(
        "C:\\Projects\\app-builder\\signal\\src\\signal"
    ).project_id == "signal"
    assert registry.project_for_root(
        "C:\\Projects\\app-builder\\shared"
    ).project_id == "app-builder"


def test_registry_lookups_fail_closed() -> None:
    registry = load_project_registry_settings(REGISTRY_PATH, boundary="C:\\Projects")

    with pytest.raises(KeyError, match="unknown"):
        registry.project("unknown")
    with pytest.raises(KeyError, match="Unregistered project root"):
        registry.project_for_root("C:\\Projects\\unknown")
