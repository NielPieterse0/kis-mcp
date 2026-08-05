from __future__ import annotations

import os
import shutil
from collections.abc import Callable

from kis_mcp.tools.mcp_stdio import StdioMcpCommand

from ..contracts import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderState,
)
from .settings import GitLabProviderSettings

Which = Callable[[str], str | None]
EnvironmentPresent = Callable[[str], bool]


def _environment_present(name: str) -> bool:
    return name in os.environ


def gitlab_provider_descriptor(
    settings: GitLabProviderSettings,
    *,
    which: Which = shutil.which,
    environment_present: EnvironmentPresent = _environment_present,
) -> ProviderDescriptor:
    def build() -> StdioMcpCommand:
        return StdioMcpCommand(
            executable=settings.executable,
            arguments=(str(settings.entry_point), *settings.arguments),
            environment_names=settings.environment_names,
        )

    def readiness() -> ProviderReadiness:
        details = {
            "archived_upstream": settings.archived,
            "package_name": settings.package_name,
            "package_version": settings.package_version,
            "entry_point": str(settings.entry_point),
            "authentication_verified": False,
            "environment_names": list(settings.environment_names),
        }
        if not settings.enabled:
            return ProviderReadiness(
                provider_id="gitlab-mcp",
                state=ProviderState.DISABLED,
                summary="Archived GitLab MCP connector is disabled and uncommissioned.",
                details=details,
            )
        if which(settings.executable) is None:
            return ProviderReadiness(
                provider_id="gitlab-mcp",
                state=ProviderState.UNAVAILABLE,
                summary="Configured Node executable is unavailable.",
                details=details,
            )
        if not settings.entry_point.is_file():
            return ProviderReadiness(
                provider_id="gitlab-mcp",
                state=ProviderState.UNAVAILABLE,
                summary="Configured GitLab MCP local entry point is unavailable.",
                details=details,
            )
        required_environment_names = ("GITLAB_PERSONAL_ACCESS_TOKEN",)
        missing = sorted(
            name
            for name in required_environment_names
            if not environment_present(name)
        )
        if missing:
            return ProviderReadiness(
                provider_id="gitlab-mcp",
                state=ProviderState.DEGRADED,
                summary="GitLab MCP connector is installed but required environment references are absent.",
                details={**details, "missing_environment_names": missing},
            )
        return ProviderReadiness(
            provider_id="gitlab-mcp",
            state=ProviderState.READY,
            summary="Archived GitLab MCP connector is locally configured; live authentication remains unverified.",
            details=details,
        )

    return ProviderDescriptor(
        provider_id="gitlab-mcp",
        display_name="GitLab MCP Connector (Archived)",
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source=(
            f"{settings.source_repository}/tree/{settings.source_revision}/src/gitlab"
        ),
        source_revision=settings.source_revision,
        capabilities=(
            ProviderCapability(
                capability_id="gitlab.repository.connector",
                description="Expose the pinned archived GitLab MCP connector as an explicit external provider.",
                effects=("external_network", "remote_write"),
                tool_names=(
                    "create_branch",
                    "create_issue",
                    "create_merge_request",
                    "create_or_update_file",
                    "create_repository",
                    "fork_repository",
                    "get_file_contents",
                    "push_files",
                    "search_repositories",
                ),
            ),
        ),
        builder=build,
        readiness_probe=readiness,
        enabled=settings.enabled,
    )


__all__ = ["gitlab_provider_descriptor"]
