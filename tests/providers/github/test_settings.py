from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.providers.github.settings import (
    OFFICIAL_GITHUB_MCP_SOURCE,
    GitHubProviderSettings,
    load_github_provider_settings,
)


REVISION = "3778a41476e31a072430cfee7c5d31c5f72def60"


def _document() -> dict[str, object]:
    return {
        "schema_version": 1,
        "provider_id": "github-mcp",
        "authoritative_source": OFFICIAL_GITHUB_MCP_SOURCE,
        "source_revision": REVISION,
        "transport": "stdio",
        "executable": r"C:\Projects\.kis-mcp\github-mcp\github-mcp-server.exe",
        "token_env": "GITHUB_PERSONAL_ACCESS_TOKEN",
        "toolsets": ["all"],
        "approved_repositories": ["NielPieterse0/kis-mcp"],
        "unscoped_tools": ["get_me"],
    }


def _write(root: Path, document: dict[str, object]) -> None:
    path = root / "settings" / "providers" / "github-mcp.provider.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_loads_immutable_official_provider_settings(tmp_path: Path) -> None:
    _write(tmp_path, _document())

    settings = load_github_provider_settings(tmp_path)

    assert isinstance(settings, GitHubProviderSettings)
    assert settings.provider_id == "github-mcp"
    assert settings.source_revision == REVISION
    assert settings.toolsets == ("all",)
    assert settings.approved_repositories == ("nielpieterse0/kis-mcp",)
    assert settings.launch_args() == ("stdio", "--toolsets=all")
    with pytest.raises(AttributeError):
        settings.provider_id = "changed"  # type: ignore[misc]


def test_rejects_unknown_keys_and_secret_values(tmp_path: Path) -> None:
    document = _document()
    document["token"] = "secret"
    _write(tmp_path, document)

    with pytest.raises(RuntimeError, match="unknown keys"):
        load_github_provider_settings(tmp_path)


def test_rejects_non_official_source_and_unpinned_revision(tmp_path: Path) -> None:
    document = _document()
    document["authoritative_source"] = "https://example.com/fork"
    _write(tmp_path, document)
    with pytest.raises(RuntimeError, match="official GitHub MCP source"):
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


def test_rejects_invalid_or_duplicate_repository_scope(tmp_path: Path) -> None:
    document = _document()
    document["approved_repositories"] = ["owner/repo", "OWNER/REPO"]
    _write(tmp_path, document)
    with pytest.raises(RuntimeError, match="duplicate"):
        load_github_provider_settings(tmp_path)

    document = _document()
    document["approved_repositories"] = ["not-a-repository"]
    _write(tmp_path, document)
    with pytest.raises(RuntimeError, match="owner/repo"):
        load_github_provider_settings(tmp_path)
