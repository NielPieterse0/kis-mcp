from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any

from .contracts import Confidence, ProjectIdentity

INSPECT_CONTRACTS_SCHEMA_VERSION = 1
INSPECT_CONTRACTS_TOOL = "inspect_contracts"


def _required(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _positive(value: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _non_negative(value: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _json(value: Any) -> Any:
    if hasattr(value, "to_json_dict"):
        return value.to_json_dict()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"value is not JSON-compatible: {type(value).__name__}")


class _Record:
    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class ContractBudget(_Record):
    max_documents: int
    max_operations: int
    max_schemas: int
    max_relationships: int

    def __post_init__(self) -> None:
        for name in (
            "max_documents",
            "max_operations",
            "max_schemas",
            "max_relationships",
        ):
            _positive(getattr(self, name), f"contract budget {name}")


@dataclass(frozen=True, slots=True)
class InspectContractsRequest(_Record):
    project: str
    budget: ContractBudget

    def __post_init__(self) -> None:
        _required(self.project, "contract project")
        if not isinstance(self.budget, ContractBudget):
            raise ValueError("contract budget must be a ContractBudget")


@dataclass(frozen=True, slots=True)
class ContractDocument(_Record):
    path: str
    kind: str
    version: str | None
    title: str | None
    provenance: str = "local_json"

    def __post_init__(self) -> None:
        _required(self.path, "contract document path")
        if self.kind not in {"openapi", "json_schema", "mcp_contract"}:
            raise ValueError("contract document kind is unsupported")
        if self.version is not None:
            _required(self.version, "contract document version")
        if self.title is not None:
            _required(self.title, "contract document title")
        _required(self.provenance, "contract document provenance")


@dataclass(frozen=True, slots=True)
class ContractOperation(_Record):
    operation_id: str
    document: str
    method: str
    path: str
    summary: str | None
    request_refs: tuple[str, ...]
    response_refs: tuple[str, ...]
    provenance: str = "openapi_json"

    def __post_init__(self) -> None:
        for value, label in (
            (self.operation_id, "contract operation id"),
            (self.document, "contract operation document"),
            (self.method, "contract operation method"),
            (self.path, "contract operation path"),
            (self.provenance, "contract operation provenance"),
        ):
            _required(value, label)
        if self.summary is not None:
            _required(self.summary, "contract operation summary")


@dataclass(frozen=True, slots=True)
class ContractSchema(_Record):
    schema_id: str
    document: str
    name: str
    schema_type: str | None
    required: tuple[str, ...]
    property_count: int
    provenance: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.schema_id, "contract schema id"),
            (self.document, "contract schema document"),
            (self.name, "contract schema name"),
            (self.provenance, "contract schema provenance"),
        ):
            _required(value, label)
        if self.schema_type is not None:
            _required(self.schema_type, "contract schema type")
        _non_negative(self.property_count, "contract schema property_count")


@dataclass(frozen=True, slots=True)
class ContractRelationship(_Record):
    kind: str
    source: str
    target: str
    document: str
    provenance: str

    def __post_init__(self) -> None:
        if self.kind not in {"ref", "request_schema", "response_schema"}:
            raise ValueError("contract relationship kind is unsupported")
        for value, label in (
            (self.source, "contract relationship source"),
            (self.target, "contract relationship target"),
            (self.document, "contract relationship document"),
            (self.provenance, "contract relationship provenance"),
        ):
            _required(value, label)


@dataclass(frozen=True, slots=True)
class ContractUnknown(_Record):
    code: str
    reason: str
    path: str | None = None

    def __post_init__(self) -> None:
        _required(self.code, "contract unknown code")
        _required(self.reason, "contract unknown reason")
        if self.path is not None:
            _required(self.path, "contract unknown path")


@dataclass(frozen=True, slots=True)
class ContractOmissions(_Record):
    documents: int
    operations: int
    schemas: int
    relationships: int

    def __post_init__(self) -> None:
        for name in ("documents", "operations", "schemas", "relationships"):
            _non_negative(getattr(self, name), f"contract omissions {name}")


@dataclass(frozen=True, slots=True)
class InspectContractsResponse:
    project: ProjectIdentity
    documents: tuple[ContractDocument, ...]
    operations: tuple[ContractOperation, ...]
    schemas: tuple[ContractSchema, ...]
    relationships: tuple[ContractRelationship, ...]
    unknowns: tuple[ContractUnknown, ...]
    omissions: ContractOmissions
    confidence: Confidence
    truncated: bool
    truncation_reasons: tuple[str, ...]
    fingerprint: str
    schema_version: int = INSPECT_CONTRACTS_SCHEMA_VERSION
    tool: str = INSPECT_CONTRACTS_TOOL

    def __post_init__(self) -> None:
        if self.schema_version != INSPECT_CONTRACTS_SCHEMA_VERSION:
            raise ValueError("inspect_contracts schema_version must be 1")
        if self.tool != INSPECT_CONTRACTS_TOOL:
            raise ValueError("inspect_contracts tool identity is fixed")
        if self.truncated != bool(self.truncation_reasons):
            raise ValueError("inspect_contracts truncation state is inconsistent")
        if len(self.fingerprint) != 64 or any(
            character not in "0123456789abcdef" for character in self.fingerprint
        ):
            raise ValueError(
                "contract fingerprint must be 64 lowercase hexadecimal characters"
            )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool": self.tool,
            "project": self.project.to_json_dict(),
            "documents": _json(self.documents),
            "operations": _json(self.operations),
            "schemas": _json(self.schemas),
            "relationships": _json(self.relationships),
            "unknowns": _json(self.unknowns),
            "omissions": self.omissions.to_json_dict(),
            "confidence": self.confidence.value,
            "truncated": self.truncated,
            "truncation_reasons": list(self.truncation_reasons),
            "fingerprint": self.fingerprint,
        }


__all__ = [
    "ContractBudget",
    "ContractDocument",
    "ContractOmissions",
    "ContractOperation",
    "ContractRelationship",
    "ContractSchema",
    "ContractUnknown",
    "InspectContractsRequest",
    "InspectContractsResponse",
]
