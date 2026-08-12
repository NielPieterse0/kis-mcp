from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from kis_mcp.projects import load_project_registry_settings
from kis_mcp.providers.contracts import (
    ProviderBoundary, ProviderCapability, ProviderDescriptor, ProviderKind,
    ProviderReadiness, ProviderState,
)
from kis_mcp.providers.registry import ProviderRegistry

from .adapter import DockerHubAdapter, INTERNAL_PAT_ENV
from .settings import ALL_TOOLS, PUBLIC_TOOLS, DockerHubSettings, load_dockerhub_settings

_INSTALL_KEYS = {"provider_id", "source_revision", "entry_point_sha256"}
_MUTATING_TOOLS = {"createRepository", "updateRepositoryInfo"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def installation_manifest_path(settings: DockerHubSettings) -> Path:
    return settings.entry_point.parent.parent / "installation.json"

def validate_installation(settings: DockerHubSettings) -> None:
    if not settings.entry_point.is_file():
        raise RuntimeError("DOCKERHUB_NOT_INSTALLED")
    path = installation_manifest_path(settings)
    try:
        manifest: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("DOCKERHUB_INSTALLATION_IDENTITY_MISSING") from exc
    expected = {
        "provider_id": "dockerhub-mcp",
        "source_revision": settings.source_revision,
        "entry_point_sha256": _sha256(settings.entry_point),
    }
    if not isinstance(manifest, Mapping) or set(manifest) != _INSTALL_KEYS or dict(manifest) != expected:
        raise RuntimeError("DOCKERHUB_INSTALLATION_IDENTITY_MISMATCH")


def _commissioning(installed: bool, auth_ready: bool, mode: str) -> dict[str, str]:
    return {
        "installed": "ready" if installed else "required",
        "configured": "ready",
        "authenticated": "not_required_public" if mode == "public" else ("ready" if auth_ready else "required"),
        "upstream_connected": "pending_live_verification" if installed and auth_ready else "blocked",
        "tools_discovered": "pending_live_verification" if installed and auth_ready else "blocked",
        "live_verified": "pending",
    }


def dockerhub_readiness(settings: DockerHubSettings, environment: Mapping[str, str]) -> ProviderReadiness:
    installed = True
    try:
        validate_installation(settings)
    except RuntimeError:
        installed = False
    auth_ready = settings.auth_mode == "public" or bool(environment.get(INTERNAL_PAT_ENV))
    if not installed:
        state = ProviderState.UNAVAILABLE
        label = "Unavailable — Docker Hub pinned installation required"
        action = "Run the supervised Docker Hub bootstrap, then restart KIS."
    elif not auth_ready:
        state = ProviderState.DEGRADED
        label = "Degraded — Docker Hub PAT is not commissioned"
        action = "Set the configured Docker Hub PAT secret reference and restart KIS."
    else:
        state = ProviderState.READY
        label = "Ready — Docker Hub local preflight complete"
        action = "Run live commissioning to verify upstream connection and tool discovery."
    projects = load_project_registry_settings()
    routed = [project.project_id for project in projects.projects if project.dockerhub is not None]
    return ProviderReadiness(
        provider_id="dockerhub-mcp",
        state=state,
        summary=label,
        details={
            "source_revision": settings.source_revision,
            "auth_mode": settings.auth_mode,
            "project_bindings": routed,
            "public_tools": list(PUBLIC_TOOLS),
            "user_status": {"state": state.value, "label": label, "required_action": action},
            "commissioning": _commissioning(installed, auth_ready, settings.auth_mode),
        },
    )


def _capability_fragment(tool_name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", tool_name).casefold()


def _capabilities(settings: DockerHubSettings) -> tuple[ProviderCapability, ...]:
    exposed = ALL_TOOLS if settings.auth_mode == "pat" else PUBLIC_TOOLS
    capabilities: list[ProviderCapability] = []
    for tool in exposed:
        mutation = tool in _MUTATING_TOOLS
        capabilities.append(
            ProviderCapability(
                capability_id=f"dockerhub.{_capability_fragment(tool)}",
                description=(
                    f"Docker Hub {'account/repository mutation' if mutation else 'metadata read'} via the pinned official MCP provider; "
                    f"authentication mode is {settings.auth_mode}. Local Docker Engine operations are separate."
                ),
                effects=("external_network",) if mutation else ("external_network", "repository_read"),
                tool_names=(tool,),
            )
        )
    return tuple(capabilities)


def dockerhub_provider_descriptor(
    *, repository_root: Path | None = None, environment: Mapping[str, str]
) -> ProviderDescriptor:
    settings = load_dockerhub_settings(repository_root)
    adapter = DockerHubAdapter(settings, environment=environment)
    return ProviderDescriptor(
        provider_id="dockerhub-mcp",
        display_name="Docker Hub MCP",
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source=settings.authoritative_source,
        source_revision=settings.source_revision,
        capabilities=_capabilities(settings),
        builder=lambda: (validate_installation(settings), adapter.build_server())[1],
        readiness_probe=lambda: dockerhub_readiness(settings, environment),
    )


def register_dockerhub_provider(
    registry: ProviderRegistry,
    *, repository_root: Path | None = None, environment: Mapping[str, str]
) -> ProviderDescriptor:
    return registry.register(
        dockerhub_provider_descriptor(repository_root=repository_root, environment=environment)
    )


__all__ = [
    "dockerhub_provider_descriptor",
    "dockerhub_readiness",
    "installation_manifest_path",
    "register_dockerhub_provider",
    "validate_installation",
]
