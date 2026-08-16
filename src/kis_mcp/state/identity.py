from __future__ import annotations

import hashlib
import ntpath
import re
from typing import Mapping

from kis_mcp.paths import (
    PathValidationError,
    is_within_windows_boundary,
    normalize_windows_path,
)

from .contract import (
    IDENTITY_CONTRACT,
    OWNERSHIP_SPECS,
    SCHEMA_VERSION,
    SOURCE_IDENTITY,
    SPEC_BY_CLASS,
    StateNamespaceError,
    StateNamespaceRequest,
    StateOwnershipClass,
)

_identity = IDENTITY_CONTRACT
_source_identity = SOURCE_IDENTITY
_logical_rule = _identity["logical_id"]
_change_rule = _identity["governed_change_id"]
_source_rule = _identity["source_id"]
_worktree_rule = _identity["worktree_root"]
_LOGICAL_ID = re.compile(str(_logical_rule["pattern"]))
_GOVERNED_CHANGE_ID = re.compile(str(_change_rule["pattern"]))
_SOURCE_ID = re.compile(str(_source_rule["pattern"]))
_MAX_LOGICAL_ID = int(_logical_rule["max_length"])
_IDENTITY_KEYS = frozenset(
    key for spec in OWNERSHIP_SPECS for key in spec.required_identity_keys
)
_RULE_BY_KEY = {
    **{str(key): "logical_id" for key in _logical_rule["applies_to"] if key != "state_key"},
    "source_id": "source_id",
}


def _apply_text_canonicalization(value: str, operations: object) -> str:
    normalized = value
    for operation in operations:
        if operation == "strip":
            normalized = normalized.strip()
        elif operation == "casefold":
            normalized = normalized.casefold()
        else:
            raise RuntimeError(
                f"STATE_CONTRACT_INVALID: unsupported text canonicalization {operation}"
            )
    return normalized


def normalize_logical_id(value: object, label: str, *, error_code: str = "STATE_IDENTITY_INVALID") -> str:
    if not isinstance(value, str) or not value.strip():
        raise StateNamespaceError(
            error_code,
            f"{label} must be a non-empty identifier",
            {"identity_key": label},
        )
    normalized = _apply_text_canonicalization(value, _logical_rule["canonicalization"])
    if len(normalized) > _MAX_LOGICAL_ID or _LOGICAL_ID.fullmatch(normalized) is None:
        raise StateNamespaceError(
            error_code,
            f"{label} must use lower-case kebab identity syntax",
            {"identity_key": label},
        )
    return normalized


def normalize_source_id(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StateNamespaceError(
            "STATE_IDENTITY_INVALID",
            "source_id must be a non-empty source identity",
            {"identity_key": "source_id"},
        )
    normalized = _apply_text_canonicalization(value, _source_rule["canonicalization"])
    if _SOURCE_ID.fullmatch(normalized) is None:
        raise StateNamespaceError(
            "STATE_IDENTITY_INVALID",
            "source_id must be derived from a governed change or worktree root",
            {"identity_key": "source_id"},
        )
    return normalized


def _normalize_identity_value(key: str, value: object) -> str:
    rule = _RULE_BY_KEY.get(key)
    if rule == "source_id":
        return normalize_source_id(value)
    if rule == "logical_id":
        return normalize_logical_id(value, key)
    raise StateNamespaceError(
        "STATE_IDENTITY_UNEXPECTED",
        "identity key is not part of the state ownership contract",
        {"identity_key": key},
    )


def normalize_identity_mapping(
    values: Mapping[str, str] | None,
    *,
    required: tuple[str, ...],
    label: str,
) -> dict[str, str]:
    if values is None:
        values = {}
    if not isinstance(values, Mapping):
        raise StateNamespaceError("STATE_IDENTITY_INVALID", f"{label} must be a mapping")
    normalized: dict[str, str] = {}
    for raw_key, raw_value in values.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise StateNamespaceError(
                "STATE_IDENTITY_INVALID",
                f"{label} contains an invalid identity key",
            )
        key = raw_key.strip().casefold()
        if key in normalized:
            raise StateNamespaceError(
                "STATE_IDENTITY_COLLISION",
                f"{label} contains duplicate normalized identity keys",
                {"identity_key": key},
            )
        if key not in _IDENTITY_KEYS:
            raise StateNamespaceError(
                "STATE_IDENTITY_UNEXPECTED",
                f"{label} contains an unsupported identity key",
                {"identity_key": key},
            )
        normalized[key] = _normalize_identity_value(key, raw_value)

    required_set = set(required)
    present_set = set(normalized)
    missing = sorted(required_set - present_set)
    extra = sorted(present_set - required_set)
    if missing:
        raise StateNamespaceError(
            "STATE_IDENTITY_MISSING",
            f"{label} is missing required identity keys",
            {"missing_keys": ",".join(missing)},
        )
    if extra:
        raise StateNamespaceError(
            "STATE_IDENTITY_UNEXPECTED",
            f"{label} contains identities forbidden for this ownership class",
            {"unexpected_keys": ",".join(extra)},
        )
    return {key: normalized[key] for key in required}


def normalize_ownership(value: StateOwnershipClass | str) -> StateOwnershipClass:
    if isinstance(value, StateOwnershipClass):
        return value
    if not isinstance(value, str) or not value.strip():
        raise StateNamespaceError(
            "STATE_OWNERSHIP_INVALID",
            "ownership class must be a non-empty string",
        )
    try:
        return StateOwnershipClass(value.strip().casefold())
    except ValueError as exc:
        raise StateNamespaceError(
            "STATE_OWNERSHIP_INVALID",
            "ownership class is not defined by the state contract",
            {"ownership_class": value},
        ) from exc


def normalize_state_key(value: str | None, *, required: bool) -> str | None:
    if not required:
        if value is not None:
            raise StateNamespaceError(
                "STATE_KEY_UNEXPECTED",
                "this ownership class resolves a fixed namespace and forbids state_key",
            )
        return None
    if value is None:
        raise StateNamespaceError("STATE_KEY_MISSING", "state_key is required for this ownership class")
    return normalize_logical_id(value, "state_key", error_code="STATE_KEY_INVALID")


def derive_worktree_source_id(worktree_root: str) -> str:
    if not isinstance(worktree_root, str) or not worktree_root.strip():
        raise StateNamespaceError(
            "STATE_SOURCE_IDENTITY_INVALID",
            "worktree root must be an absolute Windows path",
        )
    boundary = str(_worktree_rule["boundary"])
    normalized = worktree_root
    try:
        for operation in _worktree_rule["canonicalization"]:
            if operation == "strip":
                normalized = normalized.strip()
            elif operation == "replace-forward-slashes":
                normalized = normalized.replace("/", "\\")
            elif operation == "normalize-windows-path":
                drive, _tail = ntpath.splitdrive(normalized)
                if not drive or not ntpath.isabs(normalized):
                    raise StateNamespaceError(
                        "STATE_SOURCE_IDENTITY_INVALID",
                        "worktree root must be an absolute Windows path",
                    )
                normalized = normalize_windows_path(normalized, base=boundary)
            elif operation == "normpath":
                normalized = ntpath.normpath(normalized)
            elif operation == "normcase":
                normalized = ntpath.normcase(normalized)
            else:
                raise RuntimeError(
                    f"STATE_CONTRACT_INVALID: unsupported worktree canonicalization {operation}"
                )
    except PathValidationError as exc:
        raise StateNamespaceError(
            "STATE_SOURCE_IDENTITY_INVALID",
            "worktree root is not a valid Windows path",
        ) from exc
    if (
        ntpath.normcase(ntpath.normpath(normalized))
        == ntpath.normcase(ntpath.normpath(boundary))
        or not is_within_windows_boundary(normalized, boundary=boundary)
    ):
        raise StateNamespaceError(
            "STATE_SOURCE_IDENTITY_INVALID",
            "worktree root must be a child of the approved project boundary",
        )
    relative = ntpath.relpath(normalized, boundary)
    parts = tuple(part for part in relative.split("\\") if part)
    if (
        len(parts) == 4
        and parts[1:3] == (".work", "worktrees")
        and _GOVERNED_CHANGE_ID.fullmatch(parts[3]) is not None
    ):
        return derive_change_source_id(parts[-1])

    digest_setting = str(_worktree_rule["digest"])
    algorithm, separator, encoding = digest_setting.partition("-")
    if not separator:
        raise RuntimeError("STATE_CONTRACT_INVALID: worktree digest must declare encoding")
    digest = hashlib.new(algorithm, normalized.encode(encoding)).hexdigest()
    return f"{_source_identity['worktree_prefix']}{digest}"


def derive_change_source_id(change_id: str) -> str:
    if not isinstance(change_id, str) or not change_id.strip():
        raise StateNamespaceError(
            "STATE_SOURCE_IDENTITY_INVALID",
            "change_id must use the governed NNN-kebab identity grammar",
        )
    normalized = _apply_text_canonicalization(change_id, _change_rule["canonicalization"])
    if _GOVERNED_CHANGE_ID.fullmatch(normalized) is None:
        raise StateNamespaceError(
            "STATE_SOURCE_IDENTITY_INVALID",
            "change_id must use the governed NNN-kebab identity grammar",
            {"identity_key": "change_id"},
        )
    return f"{_source_identity['change_prefix']}{normalized}"


def normalize_request_payload(request: StateNamespaceRequest) -> dict[str, object]:
    ownership = normalize_ownership(request.ownership)
    spec = SPEC_BY_CLASS[ownership]
    state_key = normalize_state_key(request.state_key, required=spec.state_key_required)
    identities = normalize_identity_mapping(
        request.identities,
        required=spec.required_identity_keys,
        label="identities",
    )
    expected = None
    if request.expected_identities is not None:
        expected = normalize_identity_mapping(
            request.expected_identities,
            required=spec.required_identity_keys,
            label="expected_identities",
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "ownership_class": ownership.value,
        "state_key": state_key,
        "identities": identities,
        "expected_identities": expected,
    }


__all__ = [
    "derive_change_source_id",
    "derive_worktree_source_id",
    "normalize_identity_mapping",
    "normalize_ownership",
    "normalize_request_payload",
    "normalize_source_id",
    "normalize_state_key",
]
