from __future__ import annotations

from pathlib import Path

from kis_mcp.projects import load_project_registry_settings
from kis_mcp.repositories.settings import SelectedRepositorySettings


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPOSITORY_ROOT / "settings" / "projects.settings.json"


def test_registry_backed_repository_settings_need_no_target_repo_kis_file() -> None:
    registry = load_project_registry_settings(REGISTRY_PATH, boundary="C:\\Projects")
    selected = SelectedRepositorySettings(
        registry=registry,
        boundary=Path("C:\\Projects"),
        validate_remote=False,
    )

    current = selected.current()
    gpt = selected.select(Path("C:\\Projects\\GPT-OS"))

    assert current.repository_id == "kis-mcp"
    assert gpt.repository_id == "gpt-os"
    assert gpt.github_repository == "nielpieterse0/gpt-os"
    assert gpt.github_repositories == (
        "nielpieterse0/gpt-os",
        "nielpieterse0/kis-mcp",
    )
    assert tuple(
        (item.owner, item.owner_type, item.project_number)
        for item in gpt.github_project_bindings
    ) == (("NielPieterse0", "user", 1),)


def test_registry_backed_selector_rejects_unregistered_project_root() -> None:
    registry = load_project_registry_settings(REGISTRY_PATH, boundary="C:\\Projects")
    selected = SelectedRepositorySettings(
        registry=registry,
        boundary=Path("C:\\Projects"),
        validate_remote=False,
    )

    try:
        selected.select(Path("C:\\Projects\\not-registered"))
    except RuntimeError as exc:
        assert "registered project" in str(exc)
    else:
        raise AssertionError("unregistered project root must be rejected")
