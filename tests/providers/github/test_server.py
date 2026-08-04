from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from kis_mcp.providers import (
    ProviderBoundary,
    ProviderKind,
    ProviderRegistry,
    ProviderState,
)
from kis_mcp.providers.github import server as github_server
from kis_mcp.providers.github.settings import GitHubProviderSettings


PAT = "not-for-output"


def _settings(executable: str | None = None) -> GitHubProviderSettings:
    return GitHubProviderSettings(
        schema_version=2,
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
        approved_repositories=("nielpieterse0/kis-mcp",),
        unscoped_tools=("get_me",),
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


def test_health_reports_installation_and_pat_conflict_without_claiming_authentication(
    tmp_path: Path,
) -> None:
    executable = tmp_path / "github-mcp-server.exe"
    settings = _settings(str(executable))

    missing = github_server.github_provider_health(settings, {})
    assert missing.ready is False
    assert missing.executable_present is False
    assert missing.auth_mode == "oauth"
    assert missing.pat_override_present is False
    assert missing.authenticated == "not_verified"

    executable.write_bytes(b"official-binary-placeholder")
    ready = github_server.github_provider_health(
        settings,
        {"GITHUB_PERSONAL_ACCESS_TOKEN": PAT},
    )
    assert ready.ready is True
    assert ready.executable_present is True
    assert ready.pat_override_present is True
    assert ready.authenticated == "not_verified"
    assert ready.approved_repositories == ("nielpieterse0/kis-mcp",)
    assert PAT not in str(asdict(ready))


def test_builds_token_free_official_stdio_proxy_with_scope_middleware(
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

    class FakeStatefulClient:
        def __init__(self, transport: Any) -> None:
            captured["client_transport"] = transport

        def new_stateful(self) -> str:
            return "session-client"

    class FakeProvider:
        def __init__(self, factory: Any) -> None:
            captured["provider_client"] = factory()

    proxy = FakeServer("unused")
    monkeypatch.setattr(github_server, "StdioTransport", FakeTransport)
    monkeypatch.setattr(
        github_server,
        "FastMCP",
        lambda name: captured.update(name=name) or proxy,
    )
    monkeypatch.setattr(github_server, "StatefulProxyClient", FakeStatefulClient)
    monkeypatch.setattr(github_server, "ProxyProvider", FakeProvider)

    server = github_server.build_github_provider_server(
        _settings(),
        environ={"GITHUB_PERSONAL_ACCESS_TOKEN": PAT, "PATH": "bin"},
        validate_executable=False,
    )

    assert server is proxy
    assert captured["name"] == "kis-mcp-github"
    assert captured["transport"]["command"].endswith("github-mcp-server.exe")
    assert captured["transport"]["args"] == ["stdio", "--toolsets=all"]
    assert captured["transport"]["env"] == {"PATH": "bin"}
    assert len(proxy.middlewares) == 1
    assert "kis_github_health" in proxy.tools


def test_registers_common_provider_descriptor_and_local_readiness(tmp_path: Path) -> None:
    registry = ProviderRegistry()
    executable = tmp_path / "github-mcp-server.exe"
    settings = _settings(str(executable))

    descriptor = github_server.register_github_provider(registry, settings, environ={})

    assert descriptor.provider_id == "github-mcp"
    assert descriptor.display_name == "GitHub MCP"
    assert descriptor.provider_kind is ProviderKind.CONNECTOR
    assert descriptor.boundary is ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR
    assert [item.capability_id for item in descriptor.capabilities] == [
        "repository.remote_read_write"
    ]
    assert registry.get("github-mcp") is descriptor

    unavailable = descriptor.readiness_probe()
    assert unavailable.state is ProviderState.UNAVAILABLE
    assert unavailable.details["executable_present"] is False
    assert unavailable.details["auth_mode"] == "oauth"
    assert unavailable.details["authenticated"] == "not_verified"

    executable.write_bytes(b"official-binary-placeholder")
    ready = descriptor.readiness_probe()
    assert ready.state is ProviderState.READY
    assert ready.details["executable_present"] is True
    assert ready.details["authenticated"] == "not_verified"
