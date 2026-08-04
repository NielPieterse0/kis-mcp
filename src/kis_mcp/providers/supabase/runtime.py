from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from .config import SupabaseProviderConfig


class SupabaseProviderRuntimeError(RuntimeError):
    """Raised when required runtime credentials or scope are unavailable."""


@dataclass(frozen=True, slots=True)
class SupabaseProviderReadiness:
    provider_id: str
    server_name: str
    ready: bool
    endpoint_kind: str
    source_repository: str
    source_revision: str
    project_scoped: bool
    project_ref_present: bool
    access_token_present: bool
    read_only: bool
    features: tuple[str, ...]
    upstream_transport: str
    downstream_transport: str
    verify_tls: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "server_name": self.server_name,
            "ready": self.ready,
            "endpoint_kind": self.endpoint_kind,
            "source_repository": self.source_repository,
            "source_revision": self.source_revision,
            "project_scoped": self.project_scoped,
            "project_ref_present": self.project_ref_present,
            "access_token_present": self.access_token_present,
            "read_only": self.read_only,
            "features": list(self.features),
            "upstream_transport": self.upstream_transport,
            "downstream_transport": self.downstream_transport,
            "verify_tls": self.verify_tls,
        }


def _runtime_value(
    environment: Mapping[str, str],
    name: str,
) -> str | None:
    value = environment.get(name)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def require_runtime_credentials(
    config: SupabaseProviderConfig,
    environment: Mapping[str, str],
) -> tuple[str, str]:
    project_ref = _runtime_value(environment, config.project_ref_env)
    if project_ref is None:
        raise SupabaseProviderRuntimeError(
            f"SUPABASE_PROJECT_SCOPE_REQUIRED: set {config.project_ref_env} "
            "to one development or test Supabase project reference"
        )

    access_token = _runtime_value(environment, config.access_token_env)
    if access_token is None:
        raise SupabaseProviderRuntimeError(
            f"SUPABASE_AUTHENTICATION_REQUIRED: set {config.access_token_env} "
            "to a scoped Supabase personal access token"
        )
    return project_ref, access_token


def build_upstream_url(
    config: SupabaseProviderConfig,
    environment: Mapping[str, str],
) -> str:
    project_ref, _ = require_runtime_credentials(config, environment)
    query: dict[str, str] = {"project_ref": project_ref}
    if config.read_only:
        query["read_only"] = "true"
    if config.features:
        query["features"] = ",".join(config.features)
    return f"{config.base_url}?{urlencode(query)}"


def provider_readiness(
    config: SupabaseProviderConfig,
    environment: Mapping[str, str],
) -> SupabaseProviderReadiness:
    project_ref_present = _runtime_value(environment, config.project_ref_env) is not None
    access_token_present = _runtime_value(environment, config.access_token_env) is not None
    return SupabaseProviderReadiness(
        provider_id=config.provider_id,
        server_name=config.server_name,
        ready=project_ref_present and access_token_present,
        endpoint_kind=config.endpoint_kind,
        source_repository=config.source_repository,
        source_revision=config.source_revision,
        project_scoped=True,
        project_ref_present=project_ref_present,
        access_token_present=access_token_present,
        read_only=config.read_only,
        features=config.features,
        upstream_transport=config.upstream_transport,
        downstream_transport=config.downstream_transport,
        verify_tls=config.verify_tls,
    )
