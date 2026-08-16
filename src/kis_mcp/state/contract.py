from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, cast

_CONTRACT_ROOT = Path(__file__).resolve().parents[3] / "contracts" / "state"
_CONTRACT_PATH = _CONTRACT_ROOT / "state-ownership.contract.json"
_SUPPORTED_SCHEMA_VERSION = 1
_SUPPORTED_NAMESPACE_VERSION = 1
_SUPPORTED_CONTRACT_V1_FINGERPRINT = "2a926e9bef80d12c9f75dd5b4bdbdb6c3f1a9f9ab2dfecd1c558d8f384e3d48f"


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"STATE_CONTRACT_UNAVAILABLE: unable to load {label}") from exc
    if not isinstance(document, dict):
        raise RuntimeError(f"STATE_CONTRACT_INVALID: {label} root must be an object")
    return document


def _validate_contract_document(document: dict[str, Any]) -> None:
    if type(document.get("schema_version")) is not int or document["schema_version"] != _SUPPORTED_SCHEMA_VERSION:
        raise RuntimeError("STATE_CONTRACT_INVALID: unsupported state contract schema version")
    if type(document.get("namespace_version")) is not int or document["namespace_version"] != _SUPPORTED_NAMESPACE_VERSION:
        raise RuntimeError("STATE_CONTRACT_INVALID: unsupported state namespace version")
    contract_fingerprint = hashlib.sha256(
        json.dumps(
            document,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if contract_fingerprint != _SUPPORTED_CONTRACT_V1_FINGERPRINT:
        raise RuntimeError("STATE_CONTRACT_INVALID: unsupported version-1 contract semantics")


def _load_contract(contract_path: Path = _CONTRACT_PATH) -> dict[str, Any]:
    document = _load_json_object(contract_path, label="state contract")
    _validate_contract_document(document)
    return document


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


_CONTRACT_DOCUMENT = cast(Mapping[str, Any], _freeze(_load_contract()))
SCHEMA_VERSION = _CONTRACT_DOCUMENT["schema_version"]
NAMESPACE_VERSION = _CONTRACT_DOCUMENT["namespace_version"]
APPROVED_PROJECT_BOUNDARY = _CONTRACT_DOCUMENT["project_boundary"]
APPROVED_STATE_ROOT = _CONTRACT_DOCUMENT["state_root"]
IDENTITY_CONTRACT = _CONTRACT_DOCUMENT["identity_contract"]
SOURCE_IDENTITY = _CONTRACT_DOCUMENT["source_identity"]
FINGERPRINT_CONTRACT = _CONTRACT_DOCUMENT["fingerprint_contract"]


class StateOwnershipClass(StrEnum):
    GLOBAL_AUTHORITY = "global-authority"
    GLOBAL_CACHE = "global-cache"
    SHARED_AUTH = "shared-auth"
    PROJECT_SPECIFIC = "project-specific"
    WORKTREE_SPECIFIC = "worktree-specific"
    RUNTIME_INSTANCE_SPECIFIC = "runtime-instance-specific"
    EPHEMERAL = "ephemeral"
    RECONSTRUCTIBLE_CACHE = "reconstructible-cache"
    DURABLE_EVIDENCE = "durable-evidence"
    RECOVERY_QUARANTINE = "recovery-quarantine"


class StateNamespaceErrorCode(StrEnum):
    STATE_OWNERSHIP_INVALID = "STATE_OWNERSHIP_INVALID"
    STATE_REQUEST_INVALID = "STATE_REQUEST_INVALID"
    STATE_ROOT_INVALID = "STATE_ROOT_INVALID"
    STATE_KEY_MISSING = "STATE_KEY_MISSING"
    STATE_KEY_UNEXPECTED = "STATE_KEY_UNEXPECTED"
    STATE_KEY_INVALID = "STATE_KEY_INVALID"
    STATE_IDENTITY_MISSING = "STATE_IDENTITY_MISSING"
    STATE_IDENTITY_UNEXPECTED = "STATE_IDENTITY_UNEXPECTED"
    STATE_IDENTITY_INVALID = "STATE_IDENTITY_INVALID"
    STATE_IDENTITY_COLLISION = "STATE_IDENTITY_COLLISION"
    STATE_IDENTITY_STALE = "STATE_IDENTITY_STALE"
    STATE_SOURCE_IDENTITY_INVALID = "STATE_SOURCE_IDENTITY_INVALID"
    STATE_NAMESPACE_INVALID = "STATE_NAMESPACE_INVALID"
    STATE_NAMESPACE_ESCAPE = "STATE_NAMESPACE_ESCAPE"
    STATE_NAMESPACE_COLLISION = "STATE_NAMESPACE_COLLISION"


def _validate_public_enums() -> None:
    ownership_values = [
        item["ownership_class"]
        for item in _CONTRACT_DOCUMENT["ownership_classes"]
    ]
    if ownership_values != [item.value for item in StateOwnershipClass]:
        raise RuntimeError(
            "STATE_CONTRACT_INVALID: ownership class vocabulary does not match public API"
        )
    error_values = list(_CONTRACT_DOCUMENT["resolver_contract"]["error_codes"])
    if error_values != [item.value for item in StateNamespaceErrorCode]:
        raise RuntimeError(
            "STATE_CONTRACT_INVALID: error code vocabulary does not match public API"
        )


_validate_public_enums()


@dataclass(frozen=True, slots=True)
class StateOwnershipSpec:
    ownership_class: StateOwnershipClass
    scope: str
    required_identity_keys: tuple[str, ...]
    namespace_template: str
    state_key_required: bool
    authoritative: bool
    reconstructible: bool = False

    def to_json_dict(self) -> dict[str, object]:
        return {
            "ownership_class": self.ownership_class.value,
            "scope": self.scope,
            "required_identity_keys": list(self.required_identity_keys),
            "namespace_template": self.namespace_template,
            "state_key_required": self.state_key_required,
            "authoritative": self.authoritative,
            "reconstructible": self.reconstructible,
        }


OWNERSHIP_SPECS = tuple(
    StateOwnershipSpec(
        ownership_class=StateOwnershipClass(item["ownership_class"]),
        scope=item["scope"],
        required_identity_keys=tuple(item["required_identity_keys"]),
        namespace_template=item["namespace_template"],
        state_key_required=item["state_key_required"],
        authoritative=item["authoritative"],
        reconstructible=item["reconstructible"],
    )
    for item in _CONTRACT_DOCUMENT["ownership_classes"]
)
SPEC_BY_CLASS = MappingProxyType({item.ownership_class: item for item in OWNERSHIP_SPECS})

_limits = _CONTRACT_DOCUMENT["resolver_contract"]["diagnostic_limits"]
MAX_DIAGNOSTICS = _limits["max_fields"]
MAX_DIAGNOSTIC_KEY = _limits["max_key_length"]
MAX_DIAGNOSTIC_VALUE = _limits["max_value_length"]


class StateNamespaceError(ValueError):
    def __init__(
        self,
        code: StateNamespaceErrorCode | str,
        message: str,
        diagnostics: Mapping[str, object] | None = None,
    ) -> None:
        try:
            self.code = StateNamespaceErrorCode(str(code).strip()).value
        except ValueError as exc:
            raise ValueError(f"unknown state namespace error code: {code}") from exc
        self.message = str(message).strip()
        if not self.message:
            raise ValueError("state namespace error message must be non-empty")
        bounded: dict[str, str] = {}
        for key, value in list((diagnostics or {}).items())[:MAX_DIAGNOSTICS]:
            bounded[str(key)[:MAX_DIAGNOSTIC_KEY]] = str(value)[:MAX_DIAGNOSTIC_VALUE]
        self.diagnostics = MappingProxyType(bounded)
        super().__init__(f"{self.code}: {self.message}")

    def to_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "code": self.code,
            "message": self.message,
            "diagnostics": dict(self.diagnostics),
        }


@dataclass(frozen=True, slots=True)
class StateNamespaceRequest:
    ownership: StateOwnershipClass | str
    state_key: str | None = None
    identities: Mapping[str, str] = field(default_factory=dict)
    expected_identities: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identities, Mapping):
            raise StateNamespaceError("STATE_IDENTITY_INVALID", "identities must be a mapping")
        object.__setattr__(self, "identities", MappingProxyType(dict(self.identities)))
        if self.expected_identities is not None:
            if not isinstance(self.expected_identities, Mapping):
                raise StateNamespaceError(
                    "STATE_IDENTITY_INVALID",
                    "expected_identities must be a mapping",
                )
            object.__setattr__(
                self,
                "expected_identities",
                MappingProxyType(dict(self.expected_identities)),
            )

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, object]) -> "StateNamespaceRequest":
        if not isinstance(payload, Mapping):
            raise StateNamespaceError("STATE_REQUEST_INVALID", "request payload must be a mapping")
        required = {
            "schema_version",
            "ownership_class",
            "state_key",
            "identities",
            "expected_identities",
        }
        schema_version = payload.get("schema_version")
        if (
            set(payload) != required
            or isinstance(schema_version, bool)
            or not isinstance(schema_version, (int, float))
            or schema_version != SCHEMA_VERSION
        ):
            raise StateNamespaceError(
                "STATE_REQUEST_INVALID",
                "request payload does not match the versioned wire contract",
            )
        request = cls(
            ownership=payload["ownership_class"],
            state_key=payload["state_key"],
            identities=payload["identities"],
            expected_identities=payload["expected_identities"],
        )
        if request.to_json_dict() != dict(payload):
            raise StateNamespaceError("STATE_REQUEST_INVALID", "request payload is not canonical")
        return request

    def to_json_dict(self) -> dict[str, object]:
        from .identity import normalize_request_payload

        return normalize_request_payload(self)


@dataclass(frozen=True, slots=True)
class StateNamespace:
    namespace_version: int
    ownership: StateOwnershipClass
    state_key: str | None
    identities: tuple[tuple[str, str], ...]
    relative_path: str
    path: str
    identity_fingerprint: str

    def to_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "namespace_version": self.namespace_version,
            "ownership_class": self.ownership.value,
            "state_key": self.state_key,
            "identities": dict(self.identities),
            "relative_path": self.relative_path,
            "identity_fingerprint": self.identity_fingerprint,
        }


def state_ownership_contract() -> dict[str, Any]:
    return _thaw(_CONTRACT_DOCUMENT)


__all__ = [
    "APPROVED_PROJECT_BOUNDARY",
    "APPROVED_STATE_ROOT",
    "FINGERPRINT_CONTRACT",
    "IDENTITY_CONTRACT",
    "NAMESPACE_VERSION",
    "OWNERSHIP_SPECS",
    "SOURCE_IDENTITY",
    "SCHEMA_VERSION",
    "SPEC_BY_CLASS",
    "StateNamespace",
    "StateNamespaceError",
    "StateNamespaceErrorCode",
    "StateNamespaceRequest",
    "StateOwnershipClass",
    "StateOwnershipSpec",
    "state_ownership_contract",
]
