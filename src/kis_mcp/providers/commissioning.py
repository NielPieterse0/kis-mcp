from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from kis_mcp.config import load_runtime_config

_SCHEMA_VERSION = 1
_PROVIDER_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_EVIDENCE_KEYS = {
    "schema_version",
    "provider_id",
    "identity_fingerprint",
    "identity",
    "verified_tools",
}


def commissioning_evidence_root(repository_root: Path) -> Path:
    config = load_runtime_config(repository_root)
    return Path(config.state_root) / "commissioning" / "providers"


def _normalized_identity(identity: Mapping[str, Any]) -> dict[str, Any]:
    rendered = json.dumps(dict(identity), sort_keys=True, separators=(",", ":"))
    value = json.loads(rendered)
    if not isinstance(value, dict):
        raise ValueError("commissioning identity must be an object")
    return value


def commissioning_identity_fingerprint(identity: Mapping[str, Any]) -> str:
    normalized = _normalized_identity(identity)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def commissioning_evidence_path(
    root: Path,
    provider_id: str,
    identity: Mapping[str, Any],
) -> Path:
    if _PROVIDER_ID.fullmatch(provider_id) is None:
        raise ValueError("provider_id must be lowercase hyphenated text")
    fingerprint = commissioning_identity_fingerprint(identity)
    return Path(root) / provider_id / f"{fingerprint}.json"


def _normalized_tools(tools: Sequence[str]) -> list[str]:
    values = sorted({str(tool).strip() for tool in tools if str(tool).strip()})
    if not values:
        raise ValueError("commissioning evidence requires at least one verified tool")
    return values


def _document(
    provider_id: str,
    identity: Mapping[str, Any],
    tools: Sequence[str],
) -> dict[str, Any]:
    normalized_identity = _normalized_identity(identity)
    verified_tools = _normalized_tools(tools)
    expected = normalized_identity.get("expected_tools")
    if expected is not None and verified_tools != _normalized_tools(expected):
        raise ValueError("commissioning verified tools do not match expected tool identity")
    return {
        "schema_version": _SCHEMA_VERSION,
        "provider_id": provider_id,
        "identity_fingerprint": commissioning_identity_fingerprint(normalized_identity),
        "identity": normalized_identity,
        "verified_tools": verified_tools,
    }


def read_commissioning_evidence(
    root: Path,
    provider_id: str,
    identity: Mapping[str, Any],
) -> dict[str, Any] | None:
    path = commissioning_evidence_path(root, provider_id, identity)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or set(value) != _EVIDENCE_KEYS:
        return None
    try:
        expected = _document(provider_id, identity, value.get("verified_tools", ()))
    except (TypeError, ValueError):
        return None
    return value if value == expected else None


def write_commissioning_evidence(
    root: Path,
    provider_id: str,
    identity: Mapping[str, Any],
    tools: Sequence[str],
) -> Path:
    document = _document(provider_id, identity, tools)
    path = commissioning_evidence_path(root, provider_id, identity)
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(document, indent=2, sort_keys=True) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
    except FileExistsError:
        try:
            current = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise RuntimeError("COMMISSIONING_EVIDENCE_CONFLICT") from exc
        if current != rendered:
            raise RuntimeError("COMMISSIONING_EVIDENCE_CONFLICT")
    return path


__all__ = [
    "commissioning_evidence_path",
    "commissioning_evidence_root",
    "commissioning_identity_fingerprint",
    "read_commissioning_evidence",
    "write_commissioning_evidence",
]
