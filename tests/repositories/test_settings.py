from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.repositories.settings import (
    SelectedRepositorySettings,
    load_repository_settings,
)


def _write_settings(
    root: Path,
    *,
    repository_id: str = "kis-mcp",
    github_repository: str = "NielPieterse0/kis-mcp",
    project_number: int = 1,
) -> None:
    settings = root / "settings"
    settings.mkdir(parents=True, exist_ok=True)
    (settings / "kis-repository.settings.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "repository_id": repository_id,
                "github_repository": github_repository,
                "gh_projects": [
                    {
                        "binding_id": "work-management",
                        "owner": "NielPieterse0",
                        "owner_type": "user",
                        "project_number": project_number,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_git_config(root: Path, remote: str) -> None:
    git = root / ".git"
    git.mkdir(parents=True, exist_ok=True)
    (git / "config").write_text(
        '[remote "origin"]\n' f"\turl = {remote}\n",
        encoding="utf-8",
    )


def test_loads_strict_repository_settings_and_validates_origin(tmp_path: Path) -> None:
    _write_settings(tmp_path)
    _write_git_config(tmp_path, "git@github.com:NielPieterse0/kis-mcp.git")

    settings = load_repository_settings(tmp_path)

    assert settings.repository_root == tmp_path.resolve()
    assert settings.repository_id == "kis-mcp"
    assert settings.github_repository == "nielpieterse0/kis-mcp"
    assert settings.github_owner == "nielpieterse0"
    assert settings.github_name == "kis-mcp"
    assert settings.gh_projects[0].binding_id == "work-management"
    assert settings.gh_projects[0].project_number == 1


def test_rejects_repository_identity_that_disagrees_with_origin(tmp_path: Path) -> None:
    _write_settings(tmp_path, github_repository="NielPieterse0/other")
    _write_git_config(tmp_path, "https://github.com/NielPieterse0/kis-mcp.git")

    with pytest.raises(RuntimeError, match="does not match origin"):
        load_repository_settings(tmp_path)


def test_rejects_unknown_repository_settings_keys(tmp_path: Path) -> None:
    _write_settings(tmp_path)
    path = tmp_path / "settings" / "kis-repository.settings.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["local_root"] = str(tmp_path)
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(RuntimeError, match="unknown keys"):
        load_repository_settings(tmp_path, validate_remote=False)


def test_resolves_origin_from_linked_worktree_gitdir(tmp_path: Path) -> None:
    common = tmp_path / "common.git"
    worktree_gitdir = common / "worktrees" / "change"
    worktree_gitdir.mkdir(parents=True)
    (common / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/NielPieterse0/kis-mcp.git\n',
        encoding="utf-8",
    )
    (worktree_gitdir / "commondir").write_text("../..\n", encoding="utf-8")

    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".git").write_text(
        f"gitdir: {worktree_gitdir}\n",
        encoding="utf-8",
    )
    _write_settings(checkout)

    settings = load_repository_settings(checkout)

    assert settings.github_repository == "nielpieterse0/kis-mcp"


def test_selected_repository_settings_defers_boundary_validation_until_use(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "outside" / "repo"
    boundary = tmp_path / "approved"
    repository.mkdir(parents=True)
    boundary.mkdir()
    _write_settings(repository)

    selected = SelectedRepositorySettings(
        repository,
        validate_remote=False,
        boundary=boundary,
    )

    with pytest.raises(RuntimeError, match="approved boundary"):
        selected.current()


def test_selected_repository_settings_can_switch_context(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    _write_settings(first, repository_id="first", github_repository="owner/first")
    _write_settings(second, repository_id="second", github_repository="owner/second")

    selected = SelectedRepositorySettings(first, validate_remote=False)
    first_settings = selected.current()
    second_settings = selected.select(second)

    assert first_settings.repository_id == "first"
    assert second_settings.repository_id == "second"
    assert selected.current().github_repository == "owner/second"
