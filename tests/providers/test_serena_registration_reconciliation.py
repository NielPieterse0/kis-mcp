from pathlib import Path
from types import SimpleNamespace

import pytest

from kis_mcp.providers.serena.adapter import (
    _prepare_serena_project_state,
    _reconcile_registered_projects,
)


def _write_config(path: Path, projects: list[Path], *, suffix: str = "") -> str:
    content = "header: true\nprojects:\n" + "".join(
        f"- {project}\n" for project in projects
    ) + suffix
    path.write_text(content, encoding="utf-8", newline="\n")
    return content


def test_reconcile_removes_only_missing_registered_projects(tmp_path: Path) -> None:
    active = tmp_path / "active"
    stale = tmp_path / "removed-worktree"
    active.mkdir()
    config = tmp_path / "serena_config.yml"
    _write_config(config, [active, stale], suffix="next_setting: true\n")

    removed = _reconcile_registered_projects(config)

    assert removed == (str(stale),)
    content = config.read_text(encoding="utf-8")
    assert f"- {active}\n" in content
    assert str(stale) not in content
    assert content.endswith("next_setting: true\n")


def test_reconcile_is_idempotent_when_all_projects_exist(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    config = tmp_path / "serena_config.yml"
    original = _write_config(config, [first, second])

    assert _reconcile_registered_projects(config) == ()
    assert config.read_text(encoding="utf-8") == original


def test_reconcile_rejects_ambiguous_projects_sections_without_mutation(tmp_path: Path) -> None:
    config = tmp_path / "serena_config.yml"
    original = "projects:\nprojects:\n"
    config.write_text(original, encoding="utf-8", newline="\n")

    with pytest.raises(RuntimeError, match="exactly one projects registration block"):
        _reconcile_registered_projects(config)

    assert config.read_text(encoding="utf-8") == original


def test_prepare_project_state_reconciles_before_startup(tmp_path: Path) -> None:
    active = tmp_path / "active"
    stale = tmp_path / "removed-worktree"
    active.mkdir()
    config_root = tmp_path / "config"
    config_root.mkdir()
    config = config_root / "serena_config.yml"
    config.write_text(
        'project_serena_folder_location: "C:/state/$projectFolderName/.serena"\n'
        f"projects:\n- {active}\n- {stale}\n",
        encoding="utf-8",
        newline="\n",
    )
    state_path = tmp_path / "state"
    settings = SimpleNamespace(
        project_data_root=tmp_path / "projects",
        config_root=config_root,
        project_serena_folder_template=r"C:\state\$projectFolderName\.serena",
        ensure_project_data_path=lambda _root: state_path,
    )

    assert _prepare_serena_project_state(
        settings, environment={}, project_root=str(active)
    ) == state_path
    assert str(stale) not in config.read_text(encoding="utf-8")
