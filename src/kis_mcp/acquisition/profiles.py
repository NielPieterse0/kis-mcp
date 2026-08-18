from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path, PureWindowsPath
from typing import Any

from fastmcp.exceptions import ToolError

from ..paths import PathValidationError, is_within_windows_boundary, resolve_windows_effective_path
from .settings import ProfileAuthorization

_MAX_POLICY_BYTES = 4 * 1024 * 1024
_MAX_PROFILES = 256


def _policy_path(provider_root: str, relative_path: str) -> Path:
    candidate = str(PureWindowsPath(provider_root) / PureWindowsPath(relative_path))
    try:
        effective_root = resolve_windows_effective_path(provider_root, base=provider_root, follow_final=True)
        effective_policy = resolve_windows_effective_path(candidate, base=provider_root, follow_final=True)
    except PathValidationError as exc:
        raise ToolError("PROVIDER_PROFILE_POLICY_PATH_INVALID: provider policy path could not be safely resolved") from exc
    if not is_within_windows_boundary(effective_policy, boundary=effective_root):
        raise ToolError("PROVIDER_PROFILE_POLICY_PATH_ESCAPE: provider policy resolved outside the registered project")
    return Path(effective_policy)


def _read_policy(path: Path) -> Mapping[str, Any]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ToolError("PROVIDER_PROFILE_POLICY_UNAVAILABLE: provider policy could not be read") from exc
    if len(data) > _MAX_POLICY_BYTES:
        raise ToolError("PROVIDER_PROFILE_POLICY_TOO_LARGE: provider policy exceeds 4 MiB")
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ToolError("PROVIDER_PROFILE_POLICY_INVALID: provider policy is not UTF-8 JSON") from exc
    if not isinstance(document, Mapping) or set(document) != {"schema_version", "profiles"}:
        raise ToolError("PROVIDER_PROFILE_POLICY_INVALID: provider policy root is invalid")
    version = document.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version not in {2, 3}:
        raise ToolError("PROVIDER_PROFILE_POLICY_INVALID: provider policy schema_version is unsupported")
    profiles = document.get("profiles")
    if not isinstance(profiles, list) or not 1 <= len(profiles) <= _MAX_PROFILES:
        raise ToolError("PROVIDER_PROFILE_POLICY_INVALID: provider policy profiles are invalid")
    return document


def _canonical_hash(record: Mapping[str, Any]) -> str:
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_provider_profile(
    provider_root: str,
    policy_relative_path: str,
    authorization: ProfileAuthorization,
) -> None:
    document = _read_policy(_policy_path(provider_root, policy_relative_path))
    matches = [
        item
        for item in document["profiles"]
        if isinstance(item, Mapping) and item.get("profile_id") == authorization.profile_id
    ]
    if not matches:
        raise ToolError(f"PROVIDER_PROFILE_NOT_FOUND: {authorization.profile_id}")
    if len(matches) != 1:
        raise ToolError(f"PROVIDER_PROFILE_AMBIGUOUS: {authorization.profile_id}")
    record = matches[0]
    if record.get("schema_version") != authorization.provider_profile_schema_version:
        raise ToolError("PROVIDER_PROFILE_SCHEMA_MISMATCH: provider profile version changed")
    if "enabled" in record and record.get("enabled") is not True:
        raise ToolError("PROVIDER_PROFILE_DISABLED: provider profile is not enabled")
    if _canonical_hash(record) != authorization.provider_profile_sha256:
        raise ToolError("PROVIDER_PROFILE_HASH_MISMATCH: provider profile semantics changed")


__all__ = ["verify_provider_profile"]
