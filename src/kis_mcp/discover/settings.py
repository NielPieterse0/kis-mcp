from __future__ import annotations

import codecs
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

_ROOT_KEYS = {
    "enabled",
    "limits",
    "excluded_segments",
    "allowed_extensions",
    "allowed_filenames",
    "text_encodings",
    "reject_hard_links",
}
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
class DiscoverSettings:
    enabled: bool
    limits: DiscoverLimits
    excluded_segments: tuple[str, ...]
    allowed_extensions: tuple[str, ...]
    allowed_filenames: tuple[str, ...]
    text_encodings: tuple[str, ...]
    reject_hard_links: bool

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
        )


__all__ = ["DiscoverLimits", "DiscoverSettings"]
