from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from kis_mcp.projects import ProjectRegistry, load_project_registry_settings
from kis_mcp.providers.contracts import (
    ProviderBoundary,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderState,
)
from kis_mcp.providers.registry import ProviderRegistry

from .adapter import DBHubAdapter, internal_dsn_environment, operation_name
from .settings import DBHubSettings, load_dbhub_settings

_INSTALL_KEYS = {"provider_id", "release_tag", "source_revision", "entry_point_sha256"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def installation_manifest_path(settings: DBHubSettings) -> Path:
    return settings.entry_point.parent.parent / "installation.json"


def validate_installation(settings: DBHubSettings) -> None:
    if not settings.entry_point.is_file():
        raise RuntimeError("DBHUB_NOT_INSTALLED")
    manifest_path = installation_manifest_path(settings)
    try:
        manifest: Any = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("DBHUB_INSTALLATION_IDENTITY_MISSING") from exc
    if not isinstance(manifest, Mapping) or set(manifest) != _INSTALL_KEYS:
        raise RuntimeError("DBHUB_INSTALLATION_IDENTITY_INVALID")
    expected = {
        "provider_id": "dbhub",
        "release_tag": settings.release_tag,
        "source_revision": settings.source_revision,
        "entry_point_sha256": _sha256(settings.entry_point),
    }
    if dict(manifest) != expected:
        raise RuntimeError("DBHUB_INSTALLATION_IDENTITY_MISMATCH")


def _commissioning(installed: bool, bindings_ready: bool) -> dict[str, str]:
    return {
        "installed": "ready" if installed else "required",
        "configured": "ready",
        "authenticated": "not_required" if bindings_ready else "binding_credentials_required",
        "upstream_connected": "pending_live_verification" if installed else "blocked_installation",
        "tools_discovered": "pending_live_verification" if installed else "blocked_installation",
        "live_verified": "pending",
    }


def dbhub_readiness(
    settings: DBHubSettings,
    projects: ProjectRegistry,
    environment: Mapping[str, str],
) -> ProviderReadiness:
    installed = True
    install_error: str | None = None
    try:
        validate_installation(settings)
    except RuntimeError as exc:
        installed = False
        install_error = str(exc)

    missing_bindings: list[str] = []
    local_missing: list[str] = []
    count = 0
    for project in projects.projects:
        for binding in project.databases:
            count += 1
            identity = f"{project.project_id}/{binding.binding_id}"
            if binding.boundary == "external":
                if not environment.get(internal_dsn_environment(project.project_id, binding.binding_id)):
                    missing_bindings.append(identity)
            elif binding.location is not None:
                target = Path(project.local_root) / Path(binding.location)
                if not target.is_file():
                    local_missing.append(identity)

    bindings_ready = not missing_bindings and not local_missing
    if not installed:
        state = ProviderState.UNAVAILABLE
        label = "Unavailable — DBHub pinned installation required"
        action = "Run the supervised DBHub bootstrap after the approved release/source identity is verifiable."
    elif not bindings_ready:
        state = ProviderState.DEGRADED
        label = "Degraded — database binding not commissioned"
        action = "Repair the listed local path or configure the referenced external database secret, then restart KIS."
    else:
        state = ProviderState.READY
        label = "Ready — DBHub local preflight complete"
        action = "Run live provider commissioning to verify stdio connection and tool discovery."
    return ProviderReadiness(
        provider_id="dbhub",
        state=state,
        summary=label,
        details={
            "release_tag": settings.release_tag,
            "source_revision": settings.source_revision,
            "binding_count": count,
            "missing_credential_bindings": missing_bindings,
            "missing_local_bindings": local_missing,
            "install_error": install_error,
            "user_status": {"state": state.value, "label": label, "required_action": action},
            "commissioning": _commissioning(installed, bindings_ready),
        },
    )


def _capabilities(settings: DBHubSettings, projects: ProjectRegistry) -> tuple[ProviderCapability, ...]:
    capabilities: list[ProviderCapability] = []
    for project in projects.projects:
        for binding in project.databases:
            effects = ("read_only",) if binding.boundary == "local" else ("external", "read_only")
            for tool in settings.enabled_tools:
                public_name = operation_name(project.project_id, binding.binding_id, tool)
                capabilities.append(
                    ProviderCapability(
                        capability_id=f"database.{project.project_id}.{binding.binding_id}.{tool}",
                        description=(
                            f"Read-only database operation for project {project.project_id}, binding "
                            f"{binding.binding_id}, engine {binding.engine}, boundary {binding.boundary}. "
                            + ("Discover schema objects before free-form SQL when schema is unknown." if tool == "search_objects" else "Execute read-only SQL with the configured row bound.")
                        ),
                        effects=effects,
                        tool_names=(public_name,),
                    )
                )
    return tuple(capabilities)


def dbhub_provider_descriptor(
    *,
    repository_root: Path | None = None,
    environment: Mapping[str, str],
) -> ProviderDescriptor:
    root = repository_root or Path(__file__).resolve().parents[4]
    settings = load_dbhub_settings(root)
    projects = load_project_registry_settings(root / "settings" / "projects.settings.json")
    return ProviderDescriptor(
        provider_id="dbhub",
        display_name="DBHub MCP",
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.SOURCE_AWARE_CONNECTOR,
        authoritative_source=settings.authoritative_source,
        source_revision=settings.source_revision,
        capabilities=_capabilities(settings, projects),
        builder=lambda: (
            validate_installation(settings),
            DBHubAdapter(settings, projects, environment=environment).build_server(),
        )[1],
        readiness_probe=lambda: dbhub_readiness(settings, projects, environment),
    )


def register_dbhub_provider(
    registry: ProviderRegistry,
    *,
    repository_root: Path | None = None,
    environment: Mapping[str, str],
) -> ProviderDescriptor:
    return registry.register(
        dbhub_provider_descriptor(repository_root=repository_root, environment=environment)
    )


__all__ = [
    "dbhub_provider_descriptor",
    "dbhub_readiness",
    "installation_manifest_path",
    "register_dbhub_provider",
    "validate_installation",
]
