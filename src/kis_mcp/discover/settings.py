from __future__ import annotations

import codecs
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import PureWindowsPath
from typing import Any

_ROOT_KEYS = {
    "enabled",
    "limits",
    "excluded_segments",
    "allowed_extensions",
    "allowed_filenames",
    "text_encodings",
    "reject_hard_links",
    "memory",
}
_MEMORY_KEYS = {
    "schema_version",
    "enabled",
    "state_root",
    "max_stored_bytes",
    "max_files",
    "max_modules",
    "max_symbols",
    "max_relationships",
    "fingerprint_fields",
    "provider_inclusion",
    "corruption_handling",
    "supersession_behavior",
}
_FINGERPRINT_FIELDS = frozenset({"git_revision", "dirty_tree", "settings", "provider_version"})
_CORRUPTION_HANDLING = frozenset({"refresh_and_retain", "fail_closed"})
_SUPERSESSION_BEHAVIOR = frozenset({"retain_generations"})
_LIMIT_KEYS = {
    "max_files",
    "max_directories",
    "max_total_bytes",
    "max_file_bytes",
    "max_evidence",
    "max_output_chars",
    "max_depth",
    "max_visited_entries",
    "traversal_timeout_seconds",
    "git_timeout_seconds",
    "git_max_output_bytes",
    "git_history_limit",
    "git_metadata_max_bytes",
    "python_max_nodes",
    "python_max_records",
}
_REQUEST_NARROWABLE = {
    "max_files",
    "max_directories",
    "max_total_bytes",
    "max_evidence",
    "max_output_chars",
    "max_depth",
}


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    unknown = sorted(actual - expected)
    if unknown:
        raise ValueError(f"{label} contains unsupported keys: {', '.join(unknown)}")
    if actual != expected:
        missing = sorted(expected - actual)
        raise ValueError(
            f"{label} must contain exactly the supported keys; missing: {', '.join(missing)}"
        )


def _positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value


def _choice(value: Any, label: str, allowed: frozenset[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{label} must be one of: {', '.join(sorted(allowed))}")
    return value


def _strings(value: Any, label: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{label} must be an array of strings")
    items = tuple(value)
    if not allow_empty and not items:
        raise ValueError(f"{label} must be a non-empty array of strings")
    if not all(isinstance(item, str) and item.strip() for item in items):
        raise ValueError(f"{label} must contain only non-empty strings")
    if len(set(items)) != len(items):
        raise ValueError(f"{label} must not contain duplicate values")
    return items


@dataclass(frozen=True, slots=True)
class DiscoverLimits:
    max_files: int
    max_directories: int
    max_total_bytes: int
    max_file_bytes: int
    max_evidence: int
    max_output_chars: int
    max_depth: int
    max_visited_entries: int
    traversal_timeout_seconds: int
    git_timeout_seconds: int
    git_max_output_bytes: int
    git_history_limit: int
    git_metadata_max_bytes: int
    python_max_nodes: int
    python_max_records: int

    @classmethod
    def from_mapping(cls, value: Any) -> "DiscoverLimits":
        data = _object(value, "settings.discover.limits")
        if set(data) != _LIMIT_KEYS:
            raise ValueError(
                "settings.discover.limits must contain exactly the supported limit keys"
            )
        return cls(
            **{
                key: _positive_int(data[key], f"settings.discover.limits.{key}")
                for key in sorted(_LIMIT_KEYS)
            }
        )

    def narrow(self, overrides: Mapping[str, Any] | None) -> "DiscoverLimits":
        if not overrides:
            return self
        unknown = sorted(set(overrides) - _REQUEST_NARROWABLE)
        if unknown:
            raise ValueError(f"unsupported request limit: {unknown[0]}")
        values: dict[str, int] = {}
        for key, raw_value in overrides.items():
            requested = _positive_int(raw_value, f"request limits.{key}")
            maximum = getattr(self, key)
            if requested > maximum:
                raise ValueError(f"{key} must be between 1 and {maximum}")
            values[key] = requested
        return replace(self, **values)


@dataclass(frozen=True, slots=True)
class DiscoverMemorySettings:
    schema_version: int
    enabled: bool
    state_root: str
    max_stored_bytes: int
    max_files: int
    max_modules: int
    max_symbols: int
    max_relationships: int
    fingerprint_fields: tuple[str, ...]
    provider_inclusion: tuple[str, ...]
    corruption_handling: str
    supersession_behavior: str

    @classmethod
    def from_mapping(cls, value: Any) -> "DiscoverMemorySettings":
        data = _object(value, "settings.discover.memory")
        _exact_keys(data, _MEMORY_KEYS, "settings.discover.memory")
        if data["schema_version"] != 1:
            raise ValueError("settings.discover.memory.schema_version must be 1")
        state_root = str(data["state_root"]).strip()
        path = PureWindowsPath(state_root)
        approved = PureWindowsPath(r"C:\Projects\.kis-mcp")
        if not path.is_absolute() or str(path).casefold() == str(approved).casefold():
            raise ValueError("settings.discover.memory.state_root must be beneath C:\\Projects\\.kis-mcp")
        try:
            path.relative_to(approved)
        except ValueError as exc:
            raise ValueError("settings.discover.memory.state_root must be beneath C:\\Projects\\.kis-mcp") from exc
        fields = _strings(data["fingerprint_fields"], "settings.discover.memory.fingerprint_fields")
        if set(fields) != set(_FINGERPRINT_FIELDS):
            raise ValueError("settings.discover.memory.fingerprint_fields must contain the supported fingerprint fields")
        providers = _strings(data["provider_inclusion"], "settings.discover.memory.provider_inclusion", allow_empty=True)
        return cls(
            schema_version=1,
            enabled=_boolean(data["enabled"], "settings.discover.memory.enabled"),
            state_root=str(path),
            max_stored_bytes=_positive_int(data["max_stored_bytes"], "settings.discover.memory.max_stored_bytes"),
            max_files=_positive_int(data["max_files"], "settings.discover.memory.max_files"),
            max_modules=_positive_int(data["max_modules"], "settings.discover.memory.max_modules"),
            max_symbols=_positive_int(data["max_symbols"], "settings.discover.memory.max_symbols"),
            max_relationships=_positive_int(data["max_relationships"], "settings.discover.memory.max_relationships"),
            fingerprint_fields=tuple(sorted(fields)),
            provider_inclusion=tuple(sorted(providers)),
            corruption_handling=_choice(data["corruption_handling"], "settings.discover.memory.corruption_handling", _CORRUPTION_HANDLING),
            supersession_behavior=_choice(data["supersession_behavior"], "settings.discover.memory.supersession_behavior", _SUPERSESSION_BEHAVIOR),
        )


@dataclass(frozen=True, slots=True)
class DiscoverSettings:
    enabled: bool
    limits: DiscoverLimits
    excluded_segments: tuple[str, ...]
    allowed_extensions: tuple[str, ...]
    allowed_filenames: tuple[str, ...]
    text_encodings: tuple[str, ...]
    reject_hard_links: bool
    memory: DiscoverMemorySettings = field(
        default_factory=lambda: DiscoverMemorySettings(
            schema_version=1,
            enabled=True,
            state_root=r"C:\Projects\.kis-mcp\discover",
            max_stored_bytes=25_000_000,
            max_files=5_000,
            max_modules=5_000,
            max_symbols=10_000,
            max_relationships=20_000,
            fingerprint_fields=tuple(sorted(_FINGERPRINT_FIELDS)),
            provider_inclusion=("serena",),
            corruption_handling="refresh_and_retain",
            supersession_behavior="retain_generations",
        )
    )

    @classmethod
    def from_mapping(cls, value: Any) -> "DiscoverSettings":
        data = _object(value, "settings.discover")
        _exact_keys(data, _ROOT_KEYS, "settings.discover")

        extensions = _strings(
            data["allowed_extensions"], "settings.discover.allowed_extensions"
        )
        if not all(
            item.startswith(".") and item == item.casefold() for item in extensions
        ):
            raise ValueError(
                "settings.discover.allowed_extensions must contain lowercase suffix values"
            )

        encodings = _strings(
            data["text_encodings"], "settings.discover.text_encodings"
        )
        for encoding in encodings:
            try:
                codecs.lookup(encoding)
            except LookupError as exc:
                raise ValueError(f"Unsupported text encoding: {encoding}") from exc

        return cls(
            enabled=_boolean(data["enabled"], "settings.discover.enabled"),
            limits=DiscoverLimits.from_mapping(data["limits"]),
            excluded_segments=_strings(
                data["excluded_segments"], "settings.discover.excluded_segments"
            ),
            allowed_extensions=extensions,
            allowed_filenames=_strings(
                data["allowed_filenames"],
                "settings.discover.allowed_filenames",
                allow_empty=True,
            ),
            text_encodings=encodings,
            reject_hard_links=_boolean(
                data["reject_hard_links"], "settings.discover.reject_hard_links"
            ),
            memory=DiscoverMemorySettings.from_mapping(data["memory"]),
        )


__all__ = ["DiscoverLimits", "DiscoverMemorySettings", "DiscoverSettings"]
