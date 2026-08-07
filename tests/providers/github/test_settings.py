from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.providers.github.settings import (
    OFFICIAL_GITHUB_MCP_SOURCE,
    GitHubProviderSettings,
    load_github_provider_settings,
)


REVISION = "ca8ab52dcc45b86fae190398178fd22edb7b1362"


def _document() -> dict[str, object]:
    return {
        "schema_version": 3,
        "provider_id": "github-mcp",
        "authoritative_source": OFFICIAL_GITHUB_MCP_SOURCE,
        "release_tag": "v1.8.0",
        "source_revision": REVISION,
        "transport": "stdio",
        "executable": r"C:\Projects\.kis-mcp\github-mcp\github-mcp-server.exe",
        "auth_mode": "oauth",
        "pat_env": "GITHUB_PERSONAL_ACCESS_TOKEN",
        "toolsets": ["all"],
    }


def _write(root: Path, document: dict[str, object]) -> None:
    path = root / "settings" / "providers" / "github-mcp.provider.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_loads_pinned_profile_wide_oauth_provider_settings(tmp_path: Path) -> None:
    _write(tmp_path, _document())

    settings = load_github_provider_settings(tmp_path)

    assert isinstance(settings, GitHubProviderSettings)
    assert settings.schema_version == 3
    assert settings.provider_id == "github-mcp"
    assert settings.release_tag == "v1.8.0"
    assert settings.source_revision == REVISION
    assert settings.auth_mode == "oauth"
    assert settings.pat_env == "GITHUB_PERSONAL_ACCESS_TOKEN"
    assert settings.toolsets == ("all",)
    assert settings.launch_args() == ("stdio", "--toolsets=all")
    assert not hasattr(settings, "approved_repositories")
    assert not hasattr(settings, "approved_projects")
    with pytest.raises(AttributeError):
        settings.provider_id = "changed"  # type: ignore[misc]


def test_rejects_repository_and_project_bindings_in_provider_auth_settings(
    tmp_path: Path,
) -> None:
    for key, value in (
        ("approved_repositories", ["owner/repo"]),
        ("approved_projects", [{"owner": "owner", "owner_type": "user", "project_number": 1}]),
        ("unscoped_tools", ["get_me"]),
    ):
        document = _document()
        document[key] = value
        _write(tmp_path, document)
        with pytest.raises(RuntimeError, match="unknown keys"):
            load_github_provider_settings(tmp_path)


def test_rejects_unknown_keys_and_secret_values(tmp_path: Path) -> None:
    document = _document()
    document["token"] = "secret"
    _write(tmp_path, document)

    with pytest.raises(RuntimeError, match="unknown keys"):
        load_github_provider_settings(tmp_path)


def test_rejects_pat_mode_and_legacy_token_configuration(tmp_path: Path) -> None:
    document = _document()
    document["auth_mode"] = "pat"
    _write(tmp_path, document)
    with pytest.raises(RuntimeError, match="auth_mode must be oauth"):
        load_github_provider_settings(tmp_path)

    document = _document()
    document["token_env"] = "GITHUB_PERSONAL_ACCESS_TOKEN"
    _write(tmp_path, document)
    with pytest.raises(RuntimeError, match="unknown keys"):
        load_github_provider_settings(tmp_path)


def test_rejects_non_official_source_unpinned_release_and_revision(tmp_path: Path) -> None:
    document = _document()
    document["authoritative_source"] = "https://example.com/fork"
    _write(tmp_path, document)
    with pytest.raises(RuntimeError, match="official GitHub MCP source"):
        load_github_provider_settings(tmp_path)

    document = _document()
    document["release_tag"] = "latest"
    _write(tmp_path, document)
    with pytest.raises(RuntimeError, match="release_tag"):
        load_github_provider_settings(tmp_path)

    document = _document()
    document["source_revision"] = "main"
    _write(tmp_path, document)
    with pytest.raises(RuntimeError, match="40-character"):
        load_github_provider_settings(tmp_path)


def test_rejects_executable_outside_projects_and_empty_toolsets(tmp_path: Path) -> None:
    document = _document()
    document["executable"] = r"C:\Tools\github-mcp-server.exe"
    _write(tmp_path, document)
    with pytest.raises(RuntimeError, match="beneath C:\\\\Projects"):
        load_github_provider_settings(tmp_path)

    document = _document()
    document["toolsets"] = []
    _write(tmp_path, document)
    with pytest.raises(RuntimeError, match="non-empty array"):
        load_github_provider_settings(tmp_path)
