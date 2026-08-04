from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


APPROVED_EXTERNAL_PROVIDER_IDS = frozenset({"github-mcp", "supabase"})
_SETTINGS_KEYS = frozenset({"schema_version", "providers"})
_PROVIDER_KEYS = frozenset({"provider_id", "enabled", "namespace"})
_NAMESPACE_PATTERN = re.compile(r"^[a-z][a-z0-9]*$")


class ProviderRuntimeSettingsError(RuntimeError):
    """Raised when shared provider runtime composition settings are invalid."""


@dataclass(frozen=True, slots=True)
class ProviderMountSetting:
    provider_id: str
    enabled: bool
    namespace: str

    def __post_init__(self) -> None:
        provider_id = _required_text(self.provider_id, "provider_id")
        if provider_id not in APPROVED_EXTERNAL_PROVIDER_IDS:
            raise ProviderRuntimeSettingsError(
                "provider_id must identify an approved external provider"
            )
        if not isinstance(self.enabled, bool):
            raise ProviderRuntimeSettingsError("enabled must be a boolean")
        namespace = _required_text(self.namespace, "namespace")
        if _NAMESPACE_PATTERN.fullmatch(namespace) is None:
            raise ProviderRuntimeSettingsError(
                "namespace must use lower-case alphanumeric namespace syntax"
            )
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "namespace", namespace)


@dataclass(frozen=True, slots=True)
class ProviderRuntimeSettings:
    schema_version: int
    providers: tuple[ProviderMountSetting, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ProviderRuntimeSettingsError("schema_version must be 1")
        if any(not isinstance(item, ProviderMountSetting) for item in self.providers):
            raise ProviderRuntimeSettingsError(
                "providers must contain ProviderMountSetting values"
            )
        provider_ids = [item.provider_id for item in self.providers]
        if len(set(provider_ids)) != len(provider_ids):
            raise ProviderRuntimeSettingsError(
                "providers contains duplicate provider_id values"
            )
        namespaces = [item.namespace for item in self.providers]
        if len(set(namespaces)) != len(namespaces):
            raise ProviderRuntimeSettingsError(
                "providers contains duplicate namespace values"
            )
        if set(provider_ids) != APPROVED_EXTERNAL_PROVIDER_IDS:
            raise ProviderRuntimeSettingsError(
                "providers must contain exactly the approved external providers"
            )
        object.__setattr__(
            self,
            "providers",
            tuple(sorted(self.providers, key=lambda item: item.provider_id)),
        )


def _load_document(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProviderRuntimeSettingsError(
            f"Provider runtime settings are missing: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ProviderRuntimeSettingsError(
            f"Invalid JSON in provider runtime settings {path}: {exc}"
        ) from exc
    if not isinstance(value, Mapping):
        raise ProviderRuntimeSettingsError("provider runtime settings root must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    actual = {str(key) for key in value}
    unknown = sorted(actual - expected)
    if unknown:
        raise ProviderRuntimeSettingsError(f"{label} has unknown keys: {unknown}")
    missing = sorted(expected - actual)
    if missing:
        raise ProviderRuntimeSettingsError(f"{label} is missing required keys: {missing}")


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProviderRuntimeSettingsError(f"{label} must be a non-empty string")
    return value.strip()


def _provider_entry(value: Any, index: int) -> ProviderMountSetting:
    label = f"providers[{index}]"
    if not isinstance(value, Mapping):
        raise ProviderRuntimeSettingsError(f"{label} must be an object")
    _exact_keys(value, _PROVIDER_KEYS, label)

    provider_id = _required_text(value["provider_id"], f"{label}.provider_id")
    if provider_id not in APPROVED_EXTERNAL_PROVIDER_IDS:
        raise ProviderRuntimeSettingsError(
            f"{label}.provider_id must identify an approved external provider"
        )

    enabled = value["enabled"]
    if not isinstance(enabled, bool):
        raise ProviderRuntimeSettingsError(f"{label}.enabled must be a boolean")

    namespace = _required_text(value["namespace"], f"{label}.namespace")
    if _NAMESPACE_PATTERN.fullmatch(namespace) is None:
        raise ProviderRuntimeSettingsError(
            f"{label}.namespace must use lower-case alphanumeric namespace syntax"
        )

    return ProviderMountSetting(
        provider_id=provider_id,
        enabled=enabled,
        namespace=namespace,
    )


def load_provider_runtime_settings(
    repository_root: Path | None = None,
) -> ProviderRuntimeSettings:
    root = (repository_root or Path(__file__).resolve().parents[3]).resolve()
    document = _load_document(
        root / "settings" / "providers" / "platform-runtime.provider.json"
    )
    _exact_keys(document, _SETTINGS_KEYS, "root")

    if document["schema_version"] != 1:
        raise ProviderRuntimeSettingsError("schema_version must be 1")

    raw_providers = document["providers"]
    if not isinstance(raw_providers, Sequence) or isinstance(
        raw_providers, (str, bytes, bytearray)
    ):
        raise ProviderRuntimeSettingsError("providers must be an array")

    return ProviderRuntimeSettings(
        schema_version=1,
        providers=tuple(
            _provider_entry(value, index) for index, value in enumerate(raw_providers)
        ),
    )


__all__ = [
    "APPROVED_EXTERNAL_PROVIDER_IDS",
    "ProviderMountSetting",
    "ProviderRuntimeSettings",
    "ProviderRuntimeSettingsError",
    "load_provider_runtime_settings",
]
