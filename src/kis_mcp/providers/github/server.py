from __future__ import annotations

import os
import subprocess
import sys
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
    ProviderRuntimeToolState,
    ProviderStartupCall,
    ProviderStartupPhase,
    ProviderStartupState,
)
from kis_mcp.repositories import load_repository_settings

from .auth import GitHubAuthDecision, resolve_github_shared_auth
from .routing import (
    GitHubRepositoryRouting,
    GitHubRepositoryRoutingMiddleware,
    RepositorySettingsSource,
)
from .settings import GitHubProviderSettings, load_github_provider_settings


_NOT_VERIFIED = "not_verified"
_VERIFIED = "verified"


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
    auth_source: str = "runtime_evaluation_pending"
    auth_decision: str = "runtime_evaluation_pending"
    auth_reason: str = "runtime_not_started"
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
    startup_state: ProviderStartupState | None = None,
    auth_decision: GitHubAuthDecision | None = None,
) -> GitHubProviderHealth:
    source = os.environ if environ is None else environ
    executable_present = Path(settings.executable).is_file()
    pat_override_present = bool(str(source.get(settings.pat_env, "")).strip())
    authenticated = (
        _VERIFIED
        if startup_state is not None
        and startup_state.phase is ProviderStartupPhase.READY
        else _NOT_VERIFIED
    )
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
        authenticated=authenticated,
        toolsets=settings.toolsets,
        auth_source=(
            auth_decision.source if auth_decision is not None else "runtime_evaluation_pending"
        ),
        auth_decision=(
            auth_decision.state if auth_decision is not None else "runtime_evaluation_pending"
        ),
        auth_reason=(
            auth_decision.reason if auth_decision is not None else "runtime_not_started"
        ),
    )


def _runtime_surface(environ: Mapping[str, str] | None) -> str | None:
    env = os.environ if environ is None else environ
    selected = str(env.get("KIS_MCP_RUNTIME_INSTANCE", "")).strip().casefold()
    return {
        "operation": "kis-op",
        "op": "kis-op",
        "kis-op": "kis-op",
        "development": "kis-dev",
        "dev": "kis-dev",
        "kis-dev": "kis-dev",
    }.get(selected)


def github_provider_readiness(
    settings: GitHubProviderSettings,
    environ: Mapping[str, str] | None = None,
    startup_state: ProviderStartupState | None = None,
) -> ProviderReadiness:
    health = github_provider_health(settings, environ, startup_state)
    runtime_surface = _runtime_surface(environ)
    current_runtime = (
        f"the current {runtime_surface} runtime"
        if runtime_surface is not None
        else "the current KIS runtime"
    )
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
    elif health.authenticated == _VERIFIED:
        state = ProviderState.READY
        summary = f"GitHub MCP is authenticated for {current_runtime}."
        user_status = {
            "state": "ready_authenticated",
            "label": "Ready — authenticated",
            "required_action": f"No authentication action is required for {current_runtime}.",
        }
        commissioning = {
            "installed": "ready",
            "configured": "ready",
            "authenticated": "ready",
            "upstream_connected": "ready",
            "tools_discovered": "ready",
            "live_verified": "ready",
        }
    else:
        state = ProviderState.READY
        summary = (
            "GitHub MCP is ready; runtime startup will reuse valid shared GitHub CLI auth, "
            "otherwise interactive OAuth is required."
        )
        user_status = {
            "state": "ready_authentication_bootstrap",
            "label": "Ready — authentication bootstrap pending",
            "required_action": (
                "Start the selected KIS runtime; KIS will reuse valid GitHub CLI auth first "
                "and request interactive OAuth only as fallback."
            ),
        }
        commissioning = {
            "installed": "ready",
            "configured": "ready",
            "authenticated": "bootstrap_pending",
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
    startup_state: ProviderStartupState | None = None,
    runtime_tools: ProviderRuntimeToolState | None = None,
    github_cli_config_dir: str | None = None,
    auth_runner: Callable[..., Any] = subprocess.run,
) -> FastMCP:
    runtime = settings or load_github_provider_settings()
    executable = Path(runtime.executable)
    if validate_executable and not executable.is_file():
        raise RuntimeError(
            "GitHub MCP executable is missing. Run scripts/install-github-mcp.ps1 "
            "to install the pinned official release."
        )

    resolved_auth = resolve_github_shared_auth(
        runtime,
        github_cli_config_dir=github_cli_config_dir,
        environ=environ,
        runner=auth_runner,
    )
    provider_environment = dict(resolved_auth.child_environment)
    print(
        "github_auth="
        f"{resolved_auth.decision.state} "
        f"source={resolved_auth.decision.source} "
        f"reason={resolved_auth.decision.reason}",
        file=sys.stderr,
    )
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
        startup_state=startup_state,
        runtime_tools=runtime_tools,
    )
    server = FastMCP("kis-mcp-github")
    server.add_provider(provider)

    source = repository_settings_source or load_repository_settings
    routing = GitHubRepositoryRouting(source)
    server.add_middleware(GitHubRepositoryRoutingMiddleware(routing))

    @server.tool
    def kis_github_health() -> GitHubProviderHealth:
        """Report redacted GitHub MCP installation and OAuth preflight state."""

        return github_provider_health(
            runtime,
            environ,
            provider.startup_state,
            resolved_auth.decision,
        )

    return server


def register_github_provider(
    registry: ProviderRegistry,
    settings: GitHubProviderSettings | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    repository_settings_source: RepositorySettingsSource | None = None,
) -> ProviderDescriptor:
    runtime = settings or load_github_provider_settings()
    startup_state = ProviderStartupState()
    runtime_tools = ProviderRuntimeToolState()
    descriptor = ProviderDescriptor(
        provider_id=runtime.provider_id,
        display_name="GitHub MCP",
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source=runtime.authoritative_source,
        source_revision=runtime.source_revision,
        capabilities=(
            ProviderCapability(
                capability_id="github.actions.read",
                description=(
                    "Read GitHub Actions workflow runs and jobs through the official "
                    "GitHub MCP provider."
                ),
                effects=("external_network", "repository_read"),
                tool_names=("actions_get", "actions_list"),
            ),
            ProviderCapability(
                capability_id="github.actions.trigger",
                description=(
                    "Trigger bounded GitHub Actions workflow operations through the "
                    "official GitHub MCP provider."
                ),
                effects=("external_network", "repository_write"),
                tool_names=("actions_run_trigger",),
            ),
            ProviderCapability(
                capability_id="github.pull-request.read",
                description="Read pull-request details and exact-head check runs through the official GitHub MCP provider.",
                effects=("external_network", "repository_read"),
                tool_names=("pull_request_read",),
            ),
            ProviderCapability(
                capability_id="github.pull-request.create",
                description="Create a pull request through the official GitHub MCP provider.",
                effects=("external_network", "repository_write"),
                tool_names=("create_pull_request",),
            ),
            ProviderCapability(
                capability_id="github.pull-request.merge",
                description="Merge a pull request through the official GitHub MCP provider.",
                effects=("external_network", "repository_write"),
                tool_names=("merge_pull_request",),
            ),
            ProviderCapability(
                capability_id="github.review",
                description=(
                    "Submit pull-request review state through the official GitHub MCP provider."
                ),
                effects=("external_network", "repository_write"),
                tool_names=("pull_request_review_write",),
            ),
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
            startup_state=startup_state,
            runtime_tools=runtime_tools,
        ),
        readiness_probe=lambda: github_provider_readiness(
            runtime,
            environ,
            startup_state,
        ),
        runtime_tools_probe=runtime_tools.snapshot,
    )
    return registry.register(descriptor)


def main() -> None:
    settings = load_github_provider_settings()
    server = build_github_provider_server(settings)
    server.run(transport=settings.transport)


if __name__ == "__main__":
    main()
