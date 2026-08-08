from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


OFFICIAL_REGISTRY_URL = "https://github.com/mcp/com.supabase/mcp"
OFFICIAL_SOURCE_REPOSITORY = "https://github.com/supabase/mcp"
OFFICIAL_HOSTED_ENDPOINT = "https://mcp.supabase.com/mcp"
_ENVIRONMENT_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_SOURCE_REVISION = re.compile(r"^[0-9a-f]{40}$")
_FEATURE_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")
_KEYRING_SERVICE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")


class SupabaseProviderConfigError(RuntimeError):
    """Raised when the standalone Supabase provider settings are invalid."""


@dataclass(frozen=True, slots=True)
class SupabaseProviderConfig:
    schema_version: int
    provider_id: str
    server_name: str
    registry_url: str
    source_repository: str
    source_revision: str
    upstream_transport: str
    base_url: str
    read_only: bool
    features: tuple[str, ...]
    verify_tls: bool
    auth_mode: str
    client_name: str
    token_storage: str
    keyring_service: str
    legacy_pat_env: str
    callback_host: str
    callback_timeout_seconds: int
    downstream_transport: str

    @property
    def endpoint_kind(self) -> str:
        return "hosted"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SupabaseProviderConfigError(
            f"Required Supabase provider configuration is missing: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise SupabaseProviderConfigError(
            f"Invalid JSON in Supabase provider configuration {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise SupabaseProviderConfigError("root must be an object")
    return value


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SupabaseProviderConfigError(f"{label} must be an object")
    return value


def _exact_keys(
    value: Mapping[str, Any],
    expected: set[str],
    label: str,
) -> None:
    actual = {str(key) for key in value}
    unknown = sorted(actual - expected)
    if unknown:
        raise SupabaseProviderConfigError(
            f"{label} has unknown keys: {', '.join(unknown)}"
        )
    missing = sorted(expected - actual)
    if missing:
        raise SupabaseProviderConfigError(
            f"{label} is missing required keys: {', '.join(missing)}"
        )


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SupabaseProviderConfigError(f"{label} must be a non-empty string")
    return value.strip()


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise SupabaseProviderConfigError(f"{label} must be a boolean")
    return value


def _positive_integer(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SupabaseProviderConfigError(f"{label} must be a positive integer")
    return value


def _environment_name(value: Any, label: str) -> str:
    name = _string(value, label)
    if _ENVIRONMENT_NAME.fullmatch(name) is None:
        raise SupabaseProviderConfigError(
            f"{label} must be an uppercase environment-variable name"
        )
    return name


def _features(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SupabaseProviderConfigError("upstream.features must be an array")
    features: list[str] = []
    for index, item in enumerate(value):
        feature = _string(item, f"upstream.features[{index}]")
        if _FEATURE_NAME.fullmatch(feature) is None:
            raise SupabaseProviderConfigError(
                f"upstream.features[{index}] must be a lowercase feature name"
            )
        features.append(feature)
    if len(set(features)) != len(features):
        raise SupabaseProviderConfigError(
            "upstream.features must not contain duplicates"
        )
    return tuple(features)


def _base_url(value: Any) -> str:
    raw = _string(value, "upstream.base_url")
    if raw != OFFICIAL_HOSTED_ENDPOINT:
        raise SupabaseProviderConfigError(
            "upstream.base_url must be the official hosted endpoint"
        )
    return raw


def _keyring_service(value: Any) -> str:
    service = _string(value, "authentication.keyring_service")
    if _KEYRING_SERVICE.fullmatch(service) is None:
        raise SupabaseProviderConfigError(
            "authentication.keyring_service must be a bounded keyring service name"
        )
    return service


def load_supabase_provider_config(
    repository_root: Path | None = None,
) -> SupabaseProviderConfig:
    root = (repository_root or Path(__file__).resolve().parents[4]).resolve()
    raw = _read_json(root / "settings" / "providers" / "supabase-mcp.provider.json")

    _exact_keys(
        raw,
        {
            "schema_version",
            "provider",
            "source",
            "upstream",
            "authentication",
            "downstream",
        },
        "root",
    )
    if raw["schema_version"] != 3:
        raise SupabaseProviderConfigError("schema_version must be 3")

    provider = _object(raw["provider"], "provider")
    _exact_keys(provider, {"id", "server_name"}, "provider")
    provider_id = _string(provider["id"], "provider.id")
    if provider_id != "supabase":
        raise SupabaseProviderConfigError("provider.id must be supabase")
    server_name = _string(provider["server_name"], "provider.server_name")

    source = _object(raw["source"], "source")
    _exact_keys(source, {"registry_url", "repository", "revision"}, "source")
    registry_url = _string(source["registry_url"], "source.registry_url")
    if registry_url != OFFICIAL_REGISTRY_URL:
        raise SupabaseProviderConfigError(
            "source.registry_url must identify the official MCP Registry entry"
        )
    source_repository = _string(source["repository"], "source.repository")
    if source_repository != OFFICIAL_SOURCE_REPOSITORY:
        raise SupabaseProviderConfigError(
            "source.repository must identify supabase/mcp"
        )
    source_revision = _string(source["revision"], "source.revision")
    if _SOURCE_REVISION.fullmatch(source_revision) is None:
        raise SupabaseProviderConfigError(
            "source.revision must be a 40-character lowercase commit SHA"
        )

    upstream = _object(raw["upstream"], "upstream")
    _exact_keys(
        upstream,
        {
            "transport",
            "base_url",
            "read_only",
            "features",
            "verify_tls",
        },
        "upstream",
    )
    upstream_transport = _string(upstream["transport"], "upstream.transport")
    if upstream_transport != "streamable-http":
        raise SupabaseProviderConfigError(
            "upstream.transport must be streamable-http"
        )
    verify_tls = _boolean(upstream["verify_tls"], "upstream.verify_tls")
    if not verify_tls:
        raise SupabaseProviderConfigError("upstream.verify_tls must remain true")

    authentication = _object(raw["authentication"], "authentication")
    _exact_keys(
        authentication,
        {
            "mode",
            "client_name",
            "token_storage",
            "keyring_service",
            "legacy_pat_env",
            "callback_host",
            "callback_timeout_seconds",
        },
        "authentication",
    )
    auth_mode = _string(authentication["mode"], "authentication.mode")
    if auth_mode != "oauth-dcr":
        raise SupabaseProviderConfigError(
            "authentication.mode must be oauth-dcr"
        )
    token_storage = _string(
        authentication["token_storage"], "authentication.token_storage"
    )
    if token_storage != "windows-keyring":
        raise SupabaseProviderConfigError(
            "authentication.token_storage must be windows-keyring"
        )
    callback_host = _string(
        authentication["callback_host"], "authentication.callback_host"
    )
    if callback_host != "localhost":
        raise SupabaseProviderConfigError(
            "authentication.callback_host must be localhost"
        )

    downstream = _object(raw["downstream"], "downstream")
    _exact_keys(downstream, {"transport"}, "downstream")
    downstream_transport = _string(
        downstream["transport"], "downstream.transport"
    )
    if downstream_transport != "stdio":
        raise SupabaseProviderConfigError("downstream.transport must be stdio")

    return SupabaseProviderConfig(
        schema_version=3,
        provider_id=provider_id,
        server_name=server_name,
        registry_url=registry_url,
        source_repository=source_repository,
        source_revision=source_revision,
        upstream_transport=upstream_transport,
        base_url=_base_url(upstream["base_url"]),
        read_only=_boolean(upstream["read_only"], "upstream.read_only"),
        features=_features(upstream["features"]),
        verify_tls=verify_tls,
        auth_mode=auth_mode,
        client_name=_string(
            authentication["client_name"], "authentication.client_name"
        ),
        token_storage=token_storage,
        keyring_service=_keyring_service(authentication["keyring_service"]),
        legacy_pat_env=_environment_name(
            authentication["legacy_pat_env"], "authentication.legacy_pat_env"
        ),
        callback_host=callback_host,
        callback_timeout_seconds=_positive_integer(
            authentication["callback_timeout_seconds"],
            "authentication.callback_timeout_seconds",
        ),
        downstream_transport=downstream_transport,
    )
