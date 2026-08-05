from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any

from ..contracts import Confidence, ProjectIdentity

PROJECT_CATALOG_SCHEMA_VERSION = 1
PROJECT_CATALOG_TOOL = "inspect_project_catalog"


def _required_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def _positive(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{label} must be a positive integer")


def _non_negative(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _hex_digest(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{label} must be 64 lowercase hexadecimal characters")


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
class ProjectCatalogBudget(_Record):
    max_projects: int
    max_manifests: int
    max_relationships: int
    max_unknowns: int

    def __post_init__(self) -> None:
        for name in (
            "max_projects",
            "max_manifests",
            "max_relationships",
            "max_unknowns",
        ):
            _positive(getattr(self, name), f"project catalog budget {name}")


@dataclass(frozen=True, slots=True)
class ProjectCatalogRequest(_Record):
    projects: tuple[str, ...]
    budget: ProjectCatalogBudget

    def __post_init__(self) -> None:
        if not isinstance(self.projects, tuple) or not self.projects:
            raise ValueError("project catalog projects must be a non-empty tuple")
        for value in self.projects:
            _required_text(value, "project catalog project path")
        if not isinstance(self.budget, ProjectCatalogBudget):
            raise ValueError("project catalog budget must be ProjectCatalogBudget")


@dataclass(frozen=True, slots=True)
class CatalogProject(_Record):
    project: ProjectIdentity
    selected_path: str

    def __post_init__(self) -> None:
        if not isinstance(self.project, ProjectIdentity):
            raise ValueError("catalog project identity must be ProjectIdentity")
        _required_text(self.selected_path, "catalog selected path")


@dataclass(frozen=True, slots=True)
class CatalogManifest(_Record):
    project: ProjectIdentity
    path: str
    kind: str
    content_digest: str
    provenance: str = "selected_project_manifest"

    def __post_init__(self) -> None:
        if not isinstance(self.project, ProjectIdentity):
            raise ValueError("catalog manifest project must be ProjectIdentity")
        for value, label in (
            (self.path, "catalog manifest path"),
            (self.kind, "catalog manifest kind"),
            (self.provenance, "catalog manifest provenance"),
        ):
            _required_text(value, label)
        _hex_digest(self.content_digest, "catalog manifest content_digest")


@dataclass(frozen=True, slots=True)
class ProjectRelationship(_Record):
    source_project: ProjectIdentity
    target_project: ProjectIdentity
    relationship_type: str
    source_manifest: str | None
    subject: str | None
    provenance: str
    confidence: Confidence

    def __post_init__(self) -> None:
        if not isinstance(self.source_project, ProjectIdentity):
            raise ValueError("relationship source_project must be ProjectIdentity")
        if not isinstance(self.target_project, ProjectIdentity):
            raise ValueError("relationship target_project must be ProjectIdentity")
        for value, label in (
            (self.relationship_type, "relationship type"),
            (self.provenance, "relationship provenance"),
        ):
            _required_text(value, label)
        if self.source_manifest is not None:
            _required_text(self.source_manifest, "relationship source_manifest")
        if self.subject is not None:
            _required_text(self.subject, "relationship subject")
        if self.source_project.project_id == self.target_project.project_id:
            raise ValueError("cross-project relationship cannot target its source")


@dataclass(frozen=True, slots=True)
class ProjectCatalogUnknown(_Record):
    code: str
    reason: str
    source_project: ProjectIdentity | None
    source_manifest: str | None
    candidate_path: str

    def __post_init__(self) -> None:
        _required_text(self.code, "project catalog unknown code")
        _required_text(self.reason, "project catalog unknown reason")
        _required_text(self.candidate_path, "project catalog unknown candidate_path")
        if self.source_manifest is not None:
            _required_text(self.source_manifest, "project catalog unknown source_manifest")


@dataclass(frozen=True, slots=True)
class ProjectCatalogOmissions(_Record):
    projects: int
    manifests: int
    relationships: int
    unknowns: int

    def __post_init__(self) -> None:
        for name in ("projects", "manifests", "relationships", "unknowns"):
            _non_negative(getattr(self, name), f"project catalog omissions {name}")


@dataclass(frozen=True, slots=True)
class ProjectCatalogResponse:
    projects: tuple[CatalogProject, ...]
    manifests: tuple[CatalogManifest, ...]
    relationships: tuple[ProjectRelationship, ...]
    unknowns: tuple[ProjectCatalogUnknown, ...]
    omissions: ProjectCatalogOmissions
    confidence: Confidence
    truncated: bool
    truncation_reasons: tuple[str, ...]
    fingerprint: str
    schema_version: int = PROJECT_CATALOG_SCHEMA_VERSION
    tool: str = PROJECT_CATALOG_TOOL

    def __post_init__(self) -> None:
        if self.schema_version != PROJECT_CATALOG_SCHEMA_VERSION:
            raise ValueError("project catalog schema_version must be 1")
        if self.tool != PROJECT_CATALOG_TOOL:
            raise ValueError("project catalog tool identity is fixed")
        if self.truncated != bool(self.truncation_reasons):
            raise ValueError("project catalog truncation state is inconsistent")
        _hex_digest(self.fingerprint, "project catalog fingerprint")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool": self.tool,
            "projects": _json(self.projects),
            "manifests": _json(self.manifests),
            "relationships": _json(self.relationships),
            "unknowns": _json(self.unknowns),
            "omissions": self.omissions.to_json_dict(),
            "confidence": self.confidence.value,
            "truncated": self.truncated,
            "truncation_reasons": list(self.truncation_reasons),
            "fingerprint": self.fingerprint,
        }


__all__ = [
    "CatalogManifest",
    "CatalogProject",
    "ProjectCatalogBudget",
    "ProjectCatalogOmissions",
    "ProjectCatalogRequest",
    "ProjectCatalogResponse",
    "ProjectCatalogUnknown",
    "ProjectRelationship",
]
