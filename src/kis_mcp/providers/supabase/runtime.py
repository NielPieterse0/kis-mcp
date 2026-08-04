from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import keyring
from key_value.aio.protocols import AsyncKeyValue
from key_value.aio.stores.keyring import KeyringStore
from key_value.aio.stores.keyring.store import (
    KeyringV1CollectionSanitizationStrategy,
    KeyringV1KeySanitizationStrategy,
)

from .config import SupabaseProviderConfig


class SupabaseProviderRuntimeError(RuntimeError):
    """Raised when required runtime scope or OAuth preflight is unavailable."""


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
    authentication_mode: str
    token_storage: str
    token_storage_available: bool
    legacy_pat_conflict: bool
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
            "authentication_mode": self.authentication_mode,
            "token_storage": self.token_storage,
            "token_storage_available": self.token_storage_available,
            "legacy_pat_conflict": self.legacy_pat_conflict,
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


def require_project_scope(
    config: SupabaseProviderConfig,
    environment: Mapping[str, str],
) -> str:
    project_ref = _runtime_value(environment, config.project_ref_env)
    if project_ref is None:
        raise SupabaseProviderRuntimeError(
            f"SUPABASE_PROJECT_SCOPE_REQUIRED: set {config.project_ref_env} "
            "to one development or test Supabase project reference"
        )
    return project_ref


def legacy_pat_conflict(
    config: SupabaseProviderConfig,
    environment: Mapping[str, str],
) -> bool:
    return _runtime_value(environment, config.legacy_pat_env) is not None


def build_upstream_url(
    config: SupabaseProviderConfig,
    environment: Mapping[str, str],
) -> str:
    project_ref = require_project_scope(config, environment)
    query: dict[str, str] = {"project_ref": project_ref}
    if config.read_only:
        query["read_only"] = "true"
    if config.features:
        query["features"] = ",".join(config.features)
    return f"{config.base_url}?{urlencode(query)}"


def windows_keyring_available() -> bool:
    if os.name != "nt":
        return False
    try:
        backend = keyring.get_keyring()
        priority = backend.priority
    except Exception:
        return False
    if not isinstance(priority, (int, float)) or priority <= 0:
        return False
    backend_identity = (
        f"{type(backend).__module__}.{type(backend).__qualname__}".lower()
    )
    return "fail" not in backend_identity and "null" not in backend_identity


def build_oauth_token_storage(
    config: SupabaseProviderConfig,
) -> AsyncKeyValue:
    return KeyringStore(
        service_name=config.keyring_service,
        key_sanitization_strategy=KeyringV1KeySanitizationStrategy(),
        collection_sanitization_strategy=(
            KeyringV1CollectionSanitizationStrategy()
        ),
    )


def provider_readiness(
    config: SupabaseProviderConfig,
    environment: Mapping[str, str],
    *,
    keyring_available: bool | None = None,
) -> SupabaseProviderReadiness:
    project_ref_present = _runtime_value(environment, config.project_ref_env) is not None
    pat_conflict = legacy_pat_conflict(config, environment)
    storage_available = (
        windows_keyring_available()
        if keyring_available is None
        else keyring_available
    )
    return SupabaseProviderReadiness(
        provider_id=config.provider_id,
        server_name=config.server_name,
        ready=project_ref_present and storage_available and not pat_conflict,
        endpoint_kind=config.endpoint_kind,
        source_repository=config.source_repository,
        source_revision=config.source_revision,
        project_scoped=True,
        project_ref_present=project_ref_present,
        authentication_mode=config.auth_mode,
        token_storage=config.token_storage,
        token_storage_available=storage_available,
        legacy_pat_conflict=pat_conflict,
        read_only=config.read_only,
        features=config.features,
        upstream_transport=config.upstream_transport,
        downstream_transport=config.downstream_transport,
        verify_tls=config.verify_tls,
    )
