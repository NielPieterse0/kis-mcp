from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.server import create_proxy
from fastmcp.server.providers.proxy import ProxyClient

from kis_mcp.providers import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderRegistry,
    ProviderState,
)

from .scope import GitHubRepositoryScope, GitHubRepositoryScopeMiddleware
from .settings import GitHubProviderSettings, load_github_provider_settings


@dataclass(frozen=True, slots=True)
class GitHubProviderHealth:
    ready: bool
    provider_id: str
    boundary: str
    authoritative_source: str
    source_revision: str
    executable: str
    executable_present: bool
    token_env: str
    token_present: bool
    toolsets: tuple[str, ...]
    approved_repositories: tuple[str, ...]
    schema_version: int = 1


def github_provider_environment(
    settings: GitHubProviderSettings,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    source = dict(os.environ if environ is None else environ)
    forwarded = {
        key: source[key]
        for key in ("PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT")
        if source.get(key)
    }
    token = source.get(settings.token_env)
    if token:
        forwarded[settings.token_env] = token
    return forwarded


def github_provider_health(
    settings: GitHubProviderSettings,
    environ: Mapping[str, str] | None = None,
) -> GitHubProviderHealth:
    source = os.environ if environ is None else environ
    executable_present = Path(settings.executable).is_file()
    token_present = bool(source.get(settings.token_env))
    return GitHubProviderHealth(
        ready=executable_present and token_present,
        provider_id=settings.provider_id,
        boundary="approved_external_connector",
        authoritative_source=settings.authoritative_source,
        source_revision=settings.source_revision,
        executable=settings.executable,
        executable_present=executable_present,
        token_env=settings.token_env,
        token_present=token_present,
        toolsets=settings.toolsets,
        approved_repositories=settings.approved_repositories,
    )


def github_provider_readiness(
    settings: GitHubProviderSettings,
    environ: Mapping[str, str] | None = None,
) -> ProviderReadiness:
    health = github_provider_health(settings, environ)
    state = ProviderState.READY if health.ready else ProviderState.UNAVAILABLE
    summary = (
        "GitHub MCP provider is ready."
        if health.ready
        else "GitHub MCP provider is unavailable."
    )
    return ProviderReadiness(
        provider_id=health.provider_id,
        state=state,
        summary=summary,
        details={
            "executable_present": health.executable_present,
            "token_present": health.token_present,
            "toolsets": health.toolsets,
            "approved_repositories": health.approved_repositories,
        },
    )


def build_github_provider_server(
    settings: GitHubProviderSettings | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    validate_executable: bool = True,
) -> FastMCP:
    runtime = settings or load_github_provider_settings()
    executable = Path(runtime.executable)
    if validate_executable and not executable.is_file():
        raise RuntimeError(
            "GitHub MCP executable is missing. Run scripts/install-github-mcp.ps1 "
            "with an operator-acquired official binary and expected SHA-256."
        )

    provider_environment = github_provider_environment(runtime, environ)
    transport = StdioTransport(
        command=runtime.executable,
        args=list(runtime.launch_args()),
        cwd=str(executable.parent),
        env=provider_environment,
    )
    server = create_proxy(
        ProxyClient(transport),
        name="kis-mcp-github",
    )
    scope = GitHubRepositoryScope(
        runtime.approved_repositories,
        (*runtime.unscoped_tools, "kis_github_health"),
    )
    server.add_middleware(GitHubRepositoryScopeMiddleware(scope))

    @server.tool
    def kis_github_health() -> GitHubProviderHealth:
        """Report redacted GitHub MCP connector configuration and readiness."""

        return github_provider_health(runtime, environ)

    return server


def register_github_provider(
    registry: ProviderRegistry,
    settings: GitHubProviderSettings | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> ProviderDescriptor:
    runtime = settings or load_github_provider_settings()
    descriptor = ProviderDescriptor(
        provider_id=runtime.provider_id,
        display_name="GitHub MCP",
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source=runtime.authoritative_source,
        source_revision=runtime.source_revision,
        capabilities=(
            ProviderCapability(
                capability_id="repository.remote_read_write",
                description=(
                    "Read and write approved private GitHub repositories through "
                    "the official GitHub MCP provider."
                ),
                effects=("external_network", "repository_read", "repository_write"),
            ),
        ),
        builder=lambda: build_github_provider_server(runtime, environ=environ),
        readiness_probe=lambda: github_provider_readiness(runtime, environ),
    )
    return registry.register(descriptor)


def main() -> None:
    settings = load_github_provider_settings()
    server = build_github_provider_server(settings)
    server.run(transport=settings.transport)


if __name__ == "__main__":
    main()
