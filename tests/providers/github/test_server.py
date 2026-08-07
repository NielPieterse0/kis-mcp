from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from kis_mcp.capabilities.contracts import OperationEffect
from kis_mcp.providers import (
    ProviderBoundary,
    ProviderKind,
    ProviderRegistry,
    ProviderState,
)
from kis_mcp.providers.client_runtime import PersistentClientProxyProvider
from kis_mcp.providers.github import server as github_server
from kis_mcp.providers.github.routing import GitHubRepositoryRoutingMiddleware
from kis_mcp.providers.github.settings import GitHubProviderSettings
from kis_mcp.providers.platform import provider_capability_contributions
from kis_mcp.providers.runtime import (
    ProviderMountResult,
    ProviderMountState,
    ProviderRuntimeComposition,
)
from kis_mcp.providers.service import ProviderService
from kis_mcp.repositories import GitHubProjectBinding, RepositorySettings


PAT = "not-for-output"


def _settings(executable: str | None = None) -> GitHubProviderSettings:
    return GitHubProviderSettings(
        schema_version=3,
        provider_id="github-mcp",
        authoritative_source="https://github.com/github/github-mcp-server",
        release_tag="v1.8.0",
        source_revision="ca8ab52dcc45b86fae190398178fd22edb7b1362",
        transport="stdio",
        executable=executable
        or r"C:\Projects\.kis-mcp\github-mcp\github-mcp-server.exe",
        auth_mode="oauth",
        pat_env="GITHUB_PERSONAL_ACCESS_TOKEN",
        toolsets=("all",),
    )


def _repository_settings() -> RepositorySettings:
    return RepositorySettings(
        repository_root=Path(r"C:\Projects\kis-mcp"),
        repository_id="kis-mcp",
        github_repository="nielpieterse0/kis-mcp",
        gh_projects=(
            GitHubProjectBinding(
                binding_id="work-management",
                owner="NielPieterse0",
                owner_type="user",
                project_number=1,
            ),
        ),
    )


def test_provider_environment_forwards_only_process_basics_and_never_pat() -> None:
    environment = github_server.github_provider_environment(
        _settings(),
        {
            "PATH": r"C:\Windows\System32",
            "SYSTEMROOT": r"C:\Windows",
            "GITHUB_PERSONAL_ACCESS_TOKEN": PAT,
            "UNRELATED_SECRET": "must-not-forward",
        },
    )

    assert environment == {
        "PATH": r"C:\Windows\System32",
        "SYSTEMROOT": r"C:\Windows",
    }
    assert PAT not in repr(environment)


def test_health_reports_runtime_lifetime_and_pat_conflict_without_secrets(
    tmp_path: Path,
) -> None:
    executable = tmp_path / "github-mcp-server.exe"
    settings = _settings(str(executable))

    missing = github_server.github_provider_health(settings, {})
    assert missing.ready is False
    assert missing.auth_mode == "oauth"
    assert missing.client_lifetime == "runtime"
    assert missing.auth_bootstrap_tool == "get_me"
    assert missing.authenticated == "not_verified"

    executable.write_bytes(b"official-binary-placeholder")
    ready = github_server.github_provider_health(
        settings,
        {"GITHUB_PERSONAL_ACCESS_TOKEN": PAT},
    )
    assert ready.ready is True
    assert ready.pat_override_present is True
    assert PAT not in str(asdict(ready))


def test_builds_one_persistent_token_free_official_stdio_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeServer:
        def __init__(self, name: str) -> None:
            captured["name"] = name
            self.middlewares: list[Any] = []
            self.tools: dict[str, Any] = {}
            self.providers: list[Any] = []

        def add_provider(self, provider: Any) -> None:
            self.providers.append(provider)

        def add_middleware(self, middleware: Any) -> None:
            self.middlewares.append(middleware)

        def tool(self, function: Any) -> Any:
            self.tools[function.__name__] = function
            return function

    class FakeTransport:
        def __init__(self, **kwargs: Any) -> None:
            captured["transport"] = kwargs

    class FakeClient:
        def __init__(self, transport: Any) -> None:
            captured["client_transport"] = transport

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> object:
            captured.setdefault("calls", []).append((name, arguments))
            return object()

    proxy = FakeServer("unused")
    monkeypatch.setattr(github_server, "StdioTransport", FakeTransport)
    monkeypatch.setattr(
        github_server,
        "FastMCP",
        lambda name: captured.update(name=name) or proxy,
    )

    server = github_server.build_github_provider_server(
        _settings(),
        environ={"GITHUB_PERSONAL_ACCESS_TOKEN": PAT, "PATH": "bin"},
        validate_executable=False,
        repository_settings_source=_repository_settings,
        client_factory=FakeClient,
    )

    assert server is proxy
    assert captured["name"] == "kis-mcp-github"
    assert captured["transport"]["command"].endswith("github-mcp-server.exe")
    assert captured["transport"]["args"] == ["stdio", "--toolsets=all"]
    assert captured["transport"]["env"] == {"PATH": "bin"}
    assert len(proxy.providers) == 1
    provider = proxy.providers[0]
    assert isinstance(provider, PersistentClientProxyProvider)
    assert provider.startup_call is not None
    assert provider.startup_call.tool_name == "get_me"
    assert provider.client_factory() is provider.client
    assert len(proxy.middlewares) == 1
    assert isinstance(proxy.middlewares[0], GitHubRepositoryRoutingMiddleware)
    assert "kis_github_health" in proxy.tools


def test_registers_common_provider_descriptor_and_local_readiness(tmp_path: Path) -> None:
    registry = ProviderRegistry()
    executable = tmp_path / "github-mcp-server.exe"
    settings = _settings(str(executable))

    descriptor = github_server.register_github_provider(
        registry,
        settings,
        environ={},
        repository_settings_source=_repository_settings,
    )

    assert descriptor.provider_id == "github-mcp"
    assert descriptor.display_name == "GitHub MCP"
    assert descriptor.provider_kind is ProviderKind.CONNECTOR
    assert descriptor.boundary is ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR
    assert [item.capability_id for item in descriptor.capabilities] == [
        "project_management.read",
        "project_management.write",
        "repository.remote_read_write",
    ]
    assert registry.get("github-mcp") is descriptor

    unavailable = descriptor.readiness_probe()
    assert unavailable.state is ProviderState.UNAVAILABLE
    assert unavailable.details["client_lifetime"] == "runtime"
    assert unavailable.details["auth_bootstrap_tool"] == "get_me"

    executable.write_bytes(b"official-binary-placeholder")
    ready = descriptor.readiness_probe()
    assert ready.state is ProviderState.READY
    assert ready.summary == (
        "GitHub MCP is ready; one OAuth login is required when kis-op starts."
    )
    assert ready.details["user_status"]["state"] == "ready_authentication_required"
    assert ready.details["commissioning"]["authenticated"] == (
        "required_at_runtime_start"
    )

    conflicted_descriptor = github_server.register_github_provider(
        ProviderRegistry(),
        settings,
        environ={"GITHUB_PERSONAL_ACCESS_TOKEN": PAT},
        repository_settings_source=_repository_settings,
    )
    conflicted = conflicted_descriptor.readiness_probe()
    assert conflicted.state is ProviderState.DEGRADED
    assert conflicted.details["user_status"]["state"] == "configuration_conflict"
    assert PAT not in str(conflicted.to_json_dict())


def test_project_capabilities_contribute_namespaced_operations(
    tmp_path: Path,
) -> None:
    registry = ProviderRegistry()
    descriptor = github_server.register_github_provider(
        registry,
        _settings(str(tmp_path / "github-mcp-server.exe")),
        environ={},
        repository_settings_source=_repository_settings,
    )
    composition = ProviderRuntimeComposition(
        results=(
            ProviderMountResult(
                provider_id=descriptor.provider_id,
                namespace="github",
                registered=True,
                enabled=True,
                build_attempted=True,
                built=True,
                mounted=True,
                state=ProviderMountState.MOUNTED,
            ),
        )
    )

    contribution = provider_capability_contributions(
        ProviderService(registry), composition
    )[0]
    operations = {operation.name: operation for operation in contribution.operations}

    assert set(operations) == {
        "github_projects_get",
        "github_projects_list",
        "github_projects_write",
    }
    for name in ("github_projects_get", "github_projects_list"):
        operation = operations[name]
        assert operation.capabilities == ("project_management.read",)
        assert operation.effects == (
            OperationEffect.EXTERNAL,
            OperationEffect.READ_ONLY,
        )
        assert operation.approval_required is False
    project_write = operations["github_projects_write"]
    assert project_write.capabilities == ("project_management.write",)
    assert project_write.effects == (
        OperationEffect.EXTERNAL,
        OperationEffect.LOCAL_CHANGE,
    )
