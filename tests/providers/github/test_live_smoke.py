from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from kis_mcp.providers.github import smoke
from kis_mcp.providers.github.settings import GitHubProviderSettings


def _settings() -> GitHubProviderSettings:
    return GitHubProviderSettings(
        schema_version=1,
        provider_id="github-mcp",
        authoritative_source="https://github.com/github/github-mcp-server",
        source_revision="3" * 40,
        transport="stdio",
        executable=r"C:\Projects\.kis-mcp\github-mcp\github-mcp-server.exe",
        token_env="GITHUB_PERSONAL_ACCESS_TOKEN",
        toolsets=("all",),
        approved_repositories=("nielpieterse0/kis-mcp",),
        unscoped_tools=("get_me",),
    )


def test_live_smoke_initializes_surface_auth_and_private_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    class FakeClient:
        def __init__(self, server: Any, **kwargs: Any) -> None:
            assert server == "proxy-server"
            assert kwargs["timeout"] == 60
            assert kwargs["init_timeout"] == 60

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def list_tools(self) -> list[Any]:
            return [
                SimpleNamespace(name="kis_github_health"),
                SimpleNamespace(name="get_me"),
                SimpleNamespace(name="get_file_contents"),
                SimpleNamespace(name="create_or_update_file"),
            ]

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
            calls.append((name, arguments))
            if name == "kis_github_health":
                return SimpleNamespace(
                    is_error=False,
                    data={"ready": True, "token_present": True},
                    content=[],
                )
            return SimpleNamespace(is_error=False, data={"ok": True}, content=[])

    monkeypatch.setattr(smoke, "build_github_provider_server", lambda settings: "proxy-server")
    monkeypatch.setattr(smoke, "Client", FakeClient)

    report = asyncio.run(smoke._run_live_smoke(_settings()))

    assert report == {
        "ready": True,
        "surface": True,
        "authentication": True,
        "private_repository_read": True,
        "approved_repository": "nielpieterse0/kis-mcp",
    }
    assert calls == [
        ("kis_github_health", {}),
        ("get_me", {}),
        (
            "get_file_contents",
            {
                "owner": "nielpieterse0",
                "repo": "kis-mcp",
                "path": "README.md",
            },
        ),
    ]


def test_live_smoke_rejects_missing_pinned_write_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        def __init__(self, server: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def list_tools(self) -> list[Any]:
            return [
                SimpleNamespace(name="kis_github_health"),
                SimpleNamespace(name="get_me"),
                SimpleNamespace(name="get_file_contents"),
            ]

    monkeypatch.setattr(smoke, "build_github_provider_server", lambda settings: object())
    monkeypatch.setattr(smoke, "Client", FakeClient)

    with pytest.raises(RuntimeError, match="create_or_update_file"):
        asyncio.run(smoke._run_live_smoke(_settings()))
