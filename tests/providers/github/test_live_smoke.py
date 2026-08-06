from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from kis_mcp.providers.github import commission, smoke
from kis_mcp.providers.github.settings import (
    GitHubProjectScopeSettings,
    GitHubProviderSettings,
)


def _settings() -> GitHubProviderSettings:
    return GitHubProviderSettings(
        schema_version=2,
        provider_id="github-mcp",
        authoritative_source="https://github.com/github/github-mcp-server",
        release_tag="v1.8.0",
        source_revision="ca8ab52dcc45b86fae190398178fd22edb7b1362",
        transport="stdio",
        executable=r"C:\Projects\.kis-mcp\github-mcp\github-mcp-server.exe",
        auth_mode="oauth",
        pat_env="GITHUB_PERSONAL_ACCESS_TOKEN",
        toolsets=("all",),
        approved_repositories=("nielpieterse0/kis-mcp",),
        approved_projects=(
            GitHubProjectScopeSettings(
                owner="NielPieterse0",
                owner_type="user",
                project_number=12,
            ),
        ),
        unscoped_tools=("get_me",),
    )


def _success(data: dict[str, Any] | None = None) -> Any:
    return SimpleNamespace(is_error=False, data=data or {"ok": True}, content=[])


def _error() -> Any:
    return SimpleNamespace(
        is_error=True,
        data={"message": "GITHUB_REPOSITORY_SCOPE"},
        content=[SimpleNamespace(text="GITHUB_REPOSITORY_SCOPE")],
    )


def test_commissioning_proves_oauth_private_read_and_local_repository_scope() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    class FakeClient:
        async def list_tools(self) -> list[Any]:
            return [
                SimpleNamespace(name="get_me"),
                SimpleNamespace(name="get_file_contents"),
                SimpleNamespace(name="create_or_update_file"),
            ]

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
            calls.append((name, arguments))
            if arguments.get("owner") == "github":
                return _error()
            return _success()

    report = asyncio.run(
        commission.commission_github_client(FakeClient(), _settings())
    )

    assert report == {
        "surface": True,
        "authentication": True,
        "private_repository_read": True,
        "repository_scope": True,
        "approved_repository": "nielpieterse0/kis-mcp",
        "rejected_repository": "github/github-mcp-server",
    }
    assert calls == [
        ("get_me", {}),
        (
            "get_file_contents",
            {
                "owner": "nielpieterse0",
                "repo": "kis-mcp",
                "path": "README.md",
            },
        ),
        (
            "get_file_contents",
            {
                "owner": "github",
                "repo": "github-mcp-server",
                "path": "README.md",
            },
        ),
    ]


def test_commissioning_rejects_missing_pinned_write_surface() -> None:
    class FakeClient:
        async def list_tools(self) -> list[Any]:
            return [
                SimpleNamespace(name="get_me"),
                SimpleNamespace(name="get_file_contents"),
            ]

    with pytest.raises(RuntimeError, match="create_or_update_file"):
        asyncio.run(commission.commission_github_client(FakeClient(), _settings()))


def test_commissioning_does_not_treat_unrelated_failure_as_scope_evidence() -> None:
    class FakeClient:
        async def list_tools(self) -> list[Any]:
            return [
                SimpleNamespace(name="get_me"),
                SimpleNamespace(name="get_file_contents"),
                SimpleNamespace(name="create_or_update_file"),
            ]

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
            if arguments.get("owner") == "github":
                raise RuntimeError("network failed")
            return _success()

    with pytest.raises(RuntimeError, match="network failed"):
        asyncio.run(commission.commission_github_client(FakeClient(), _settings()))


def test_shared_runtime_smoke_proves_mount_and_namespaced_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    class FakeClient:
        def __init__(self, server: Any, **kwargs: Any) -> None:
            assert server == "shared-server"
            assert kwargs["timeout"] == 120
            assert kwargs["init_timeout"] == 120

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def list_tools(self) -> list[Any]:
            return [
                SimpleNamespace(name="kis_provider_status"),
                SimpleNamespace(name="github_get_me"),
                SimpleNamespace(name="github_get_file_contents"),
                SimpleNamespace(name="github_create_or_update_file"),
            ]

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
            calls.append((name, arguments))
            if name == "kis_provider_status":
                return _success(
                    {
                        "external_providers": [
                            {
                                "provider_id": "github-mcp",
                                "mounted": True,
                                "state": "mounted",
                            }
                        ]
                    }
                )
            if arguments.get("owner") == "github":
                return _error()
            return _success()

    monkeypatch.setattr(smoke, "Client", FakeClient)

    report = asyncio.run(smoke._run_live_smoke(_settings(), "shared-server"))

    assert report == {
        "ready": True,
        "mounted": True,
        "surface": True,
        "authentication": True,
        "private_repository_read": True,
        "repository_scope": True,
        "approved_repository": "nielpieterse0/kis-mcp",
        "rejected_repository": "github/github-mcp-server",
    }
    assert calls[0] == ("kis_provider_status", {})
    assert calls[1][0] == "github_get_me"
    assert calls[2][0] == "github_get_file_contents"
    assert calls[3][0] == "github_get_file_contents"


def test_live_smoke_rejects_pat_conflict_before_building_server() -> None:
    builds = 0

    def build() -> object:
        nonlocal builds
        builds += 1
        return object()

    with pytest.raises(RuntimeError, match="GITHUB_OAUTH_PAT_CONFLICT"):
        smoke.run_live_smoke(
            build,
            settings=_settings(),
            environ={"GITHUB_PERSONAL_ACCESS_TOKEN": "forbidden-test-token"},
        )

    assert builds == 0
