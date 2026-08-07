from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastmcp import Client, FastMCP
from fastmcp.client.transports import StdioTransport

from kis_mcp.providers import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderRegistry,
    ProviderState,
)
from kis_mcp.providers.client_runtime import (
    PersistentClientProxyProvider,
    ProviderStartupCall,
)
from kis_mcp.repositories import load_repository_settings

from .routing import (
    GitHubRepositoryRouting,
    GitHubRepositoryRoutingMiddleware,
    RepositorySettingsSource,
)
from .settings import GitHubProviderSettings, load_github_provider_settings


_NOT_VERIFIED = "not_verified"


@dataclass(frozen=True, slots=True)
class GitHubProviderHealth:
    ready: bool
    provider_id: str
    boundary: str
    authoritative_source: str
    release_tag: str
    source_revision: str
    executable: str
    executable_present: bool
    auth_mode: str
    pat_env: str
    pat_override_present: bool
    authenticated: str
    toolsets: tuple[str, ...]
    client_lifetime: str = "runtime"
    auth_bootstrap_tool: str = "get_me"
    schema_version: int = 3


def github_provider_environment(
    settings: GitHubProviderSettings,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    del settings
    source = dict(os.environ if environ is None else environ)
    return {
        key: source[key]
        for key in ("PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT")
        if source.get(key)
    }


def github_provider_health(
    settings: GitHubProviderSettings,
    environ: Mapping[str, str] | None = None,
) -> GitHubProviderHealth:
    source = os.environ if environ is None else environ
    executable_present = Path(settings.executable).is_file()
    pat_override_present = bool(str(source.get(settings.pat_env, "")).strip())
    return GitHubProviderHealth(
        ready=executable_present,
        provider_id=settings.provider_id,
        boundary="approved_external_connector",
        authoritative_source=settings.authoritative_source,
        release_tag=settings.release_tag,
        source_revision=settings.source_revision,
        executable=settings.executable,
        executable_present=executable_present,
        auth_mode=settings.auth_mode,
        pat_env=settings.pat_env,
        pat_override_present=pat_override_present,
        authenticated=_NOT_VERIFIED,
        toolsets=settings.toolsets,
    )


def github_provider_readiness(
    settings: GitHubProviderSettings,
    environ: Mapping[str, str] | None = None,
) -> ProviderReadiness:
    health = github_provider_health(settings, environ)
    if not health.ready:
        state = ProviderState.UNAVAILABLE
        summary = "GitHub MCP is unavailable because the executable is not installed."
        user_status = {
            "state": "installation_required",
            "label": "Unavailable — installation required",
            "required_action": (
                "Install the pinned GitHub MCP executable before using GitHub operations."
            ),
        }
        commissioning = {
            "installed": "required",
            "configured": "pending_installation",
            "authenticated": "pending_installation",
            "upstream_connected": "pending_installation",
            "tools_discovered": "pending_installation",
            "live_verified": "pending_installation",
        }
    elif health.pat_override_present:
        state = ProviderState.DEGRADED
        summary = "GitHub MCP has a PAT override that conflicts with OAuth."
        user_status = {
            "state": "configuration_conflict",
            "label": "Action required — remove PAT override",
            "required_action": (
                "Remove GITHUB_PERSONAL_ACCESS_TOKEN before using the configured "
                "OAuth flow."
            ),
        }
        commissioning = {
            "installed": "ready",
            "configured": "conflict",
            "authenticated": "blocked_configuration",
            "upstream_connected": "blocked_configuration",
            "tools_discovered": "blocked_configuration",
            "live_verified": "blocked_configuration",
        }
    else:
        state = ProviderState.READY
        summary = (
            "GitHub MCP is ready; one OAuth login is required when kis-op starts."
        )
        user_status = {
            "state": "ready_authentication_required",
            "label": "Ready — authentication required",
            "required_action": (
                "Sign in once when kis-op starts; GitHub operations then reuse the "
                "runtime-scoped connection."
            ),
        }
        commissioning = {
            "installed": "ready",
            "configured": "ready",
            "authenticated": "required_at_runtime_start",
            "upstream_connected": "pending_authentication",
            "tools_discovered": "pending_authentication",
            "live_verified": "pending_authentication",
        }
    return ProviderReadiness(
        provider_id=health.provider_id,
        state=state,
        summary=summary,
        details={
            "release_tag": health.release_tag,
            "source_revision": health.source_revision,
            "executable_present": health.executable_present,
            "auth_mode": health.auth_mode,
            "pat_override_present": health.pat_override_present,
            "authenticated": health.authenticated,
            "toolsets": health.toolsets,
            "client_lifetime": health.client_lifetime,
            "auth_bootstrap_tool": health.auth_bootstrap_tool,
            "user_status": user_status,
            "commissioning": commissioning,
        },
    )


def build_github_provider_server(
    settings: GitHubProviderSettings | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    validate_executable: bool = True,
    repository_settings_source: RepositorySettingsSource | None = None,
    client_factory: Callable[[Any], Any] = Client,
) -> FastMCP:
    runtime = settings or load_github_provider_settings()
    executable = Path(runtime.executable)
    if validate_executable and not executable.is_file():
        raise RuntimeError(
            "GitHub MCP executable is missing. Run scripts/install-github-mcp.ps1 "
            "to install the pinned official release."
        )

    provider_environment = github_provider_environment(runtime, environ)
    transport = StdioTransport(
        command=runtime.executable,
        args=list(runtime.launch_args()),
        cwd=str(executable.parent),
        env=provider_environment,
    )
    upstream_client = client_factory(transport)
    provider = PersistentClientProxyProvider(
        upstream_client,
        startup_call=ProviderStartupCall("get_me"),
    )
    server = FastMCP("kis-mcp-github")
    server.add_provider(provider)

    source = repository_settings_source or load_repository_settings
    routing = GitHubRepositoryRouting(source)
    server.add_middleware(GitHubRepositoryRoutingMiddleware(routing))

    @server.tool
    def kis_github_health() -> GitHubProviderHealth:
        """Report redacted GitHub MCP installation and OAuth preflight state."""

        return github_provider_health(runtime, environ)

    return server


def register_github_provider(
    registry: ProviderRegistry,
    settings: GitHubProviderSettings | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    repository_settings_source: RepositorySettingsSource | None = None,
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
                capability_id="project_management.read",
                description=(
                    "Read GitHub Project metadata, fields, and items through the "
                    "official GitHub MCP provider."
                ),
                effects=("external_network", "project_read"),
                tool_names=("projects_get", "projects_list"),
            ),
            ProviderCapability(
                capability_id="project_management.write",
                description=(
                    "Add issues or pull requests to repository-bound GitHub Projects "
                    "and update bounded Project item fields."
                ),
                effects=("external_network", "project_write"),
                tool_names=("projects_write",),
            ),
            ProviderCapability(
                capability_id="repository.remote_read_write",
                description=(
                    "Read and write the explicitly selected private GitHub repository "
                    "through the official GitHub MCP provider."
                ),
                effects=("external_network", "repository_read", "repository_write"),
            ),
        ),
        builder=lambda: build_github_provider_server(
            runtime,
            environ=environ,
            repository_settings_source=repository_settings_source,
        ),
        readiness_probe=lambda: github_provider_readiness(runtime, environ),
    )
    return registry.register(descriptor)


def main() -> None:
    settings = load_github_provider_settings()
    server = build_github_provider_server(settings)
    server.run(transport=settings.transport)


if __name__ == "__main__":
    main()
