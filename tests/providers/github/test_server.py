from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from kis_mcp.provider_registry import ProviderRegistry
from kis_mcp.providers.github import server as github_server
from kis_mcp.providers.github.settings import GitHubProviderSettings


TOKEN = "not-for-output"


def _settings(executable: str | None = None) -> GitHubProviderSettings:
    return GitHubProviderSettings(
        schema_version=1,
        provider_id="github-mcp",
        authoritative_source="https://github.com/github/github-mcp-server",
        source_revision="3" * 40,
        transport="stdio",
        executable=executable
        or r"C:\Projects\.kis-mcp\github-mcp\github-mcp-server.exe",
        token_env="GITHUB_PERSONAL_ACCESS_TOKEN",
        toolsets=("all",),
        approved_repositories=("nielpieterse0/kis-mcp",),
        unscoped_tools=("get_me",),
    )


def test_provider_environment_forwards_only_process_basics_and_token() -> None:
    environment = github_server.github_provider_environment(
        _settings(),
        {
            "PATH": r"C:\Windows\System32",
            "SYSTEMROOT": r"C:\Windows",
            "GITHUB_PERSONAL_ACCESS_TOKEN": TOKEN,
            "UNRELATED_SECRET": "must-not-forward",
        },
    )

    assert environment == {
        "PATH": r"C:\Windows\System32",
        "SYSTEMROOT": r"C:\Windows",
        "GITHUB_PERSONAL_ACCESS_TOKEN": TOKEN,
    }


def test_health_is_redacted_and_requires_executable_and_token(tmp_path: Path) -> None:
    executable = tmp_path / "github-mcp-server.exe"
    settings = _settings(str(executable))

    missing = github_server.github_provider_health(settings, {})
    assert missing.ready is False
    assert missing.executable_present is False
    assert missing.token_present is False
    assert TOKEN not in repr(missing)

    executable.write_bytes(b"official-binary-placeholder")
    ready = github_server.github_provider_health(
        settings,
        {"GITHUB_PERSONAL_ACCESS_TOKEN": TOKEN},
    )
    assert ready.ready is True
    assert ready.executable_present is True
    assert ready.token_present is True
    assert ready.approved_repositories == ("nielpieterse0/kis-mcp",)
    assert TOKEN not in str(asdict(ready))


def test_builds_official_stdio_proxy_with_scope_middleware(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeProxy:
        def __init__(self) -> None:
            self.middlewares: list[Any] = []
            self.tools: dict[str, Any] = {}

        def add_middleware(self, middleware: Any) -> None:
            self.middlewares.append(middleware)

        def tool(self, function: Any) -> Any:
            self.tools[function.__name__] = function
            return function

    class FakeTransport:
        def __init__(self, **kwargs: Any) -> None:
            captured["transport"] = kwargs

    proxy = FakeProxy()
    monkeypatch.setattr(github_server, "StdioTransport", FakeTransport)
    monkeypatch.setattr(github_server, "ProxyClient", lambda transport: transport)
    monkeypatch.setattr(
        github_server,
        "create_proxy",
        lambda client, name: captured.update(client=client, name=name) or proxy,
    )

    server = github_server.build_github_provider_server(
        _settings(),
        environ={"GITHUB_PERSONAL_ACCESS_TOKEN": TOKEN, "PATH": "bin"},
        validate_executable=False,
    )

    assert server is proxy
    assert captured["name"] == "kis-mcp-github"
    assert captured["transport"]["command"].endswith("github-mcp-server.exe")
    assert captured["transport"]["args"] == ["stdio", "--toolsets=all"]
    assert captured["transport"]["env"]["GITHUB_PERSONAL_ACCESS_TOKEN"] == TOKEN
    assert len(proxy.middlewares) == 1
    assert "kis_github_health" in proxy.tools


def test_registers_builder_in_provider_registry() -> None:
    registry = ProviderRegistry()

    descriptor = github_server.register_github_provider(registry, _settings())

    assert descriptor.provider_id == "github-mcp"
    assert descriptor.boundary == "approved_external_connector"
    assert registry.get("github-mcp") is descriptor
