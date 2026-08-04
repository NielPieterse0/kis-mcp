from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


INSPECT_CHANGE_SCHEMA_VERSION = 1
INSPECT_CHANGE_TOOL = "inspect_change"
WORKING_TREE_SOURCE = "working_tree"

_CHANGE_STATUSES = {
    "added",
    "copied",
    "deleted",
    "modified",
    "renamed",
    "type_changed",
    "unmerged",
    "unknown",
}
_CHANGE_CATEGORIES = {
    "source",
    "test",
    "contract",
    "documentation",
    "configuration",
    "policy",
    "other",
}
_CONFIDENCE_VALUES = {"high", "medium", "low"}


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _non_negative(value: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class InspectChangeRequest:
    path: str
    source: str = WORKING_TREE_SOURCE

    def __post_init__(self) -> None:
        _required_text(self.path, "inspect change path")
        if self.source != WORKING_TREE_SOURCE:
            raise ValueError("inspect change source must be working_tree")


@dataclass(frozen=True, slots=True)
class ChangeIdentity:
    source: str
    fingerprint: str

    def __post_init__(self) -> None:
        if self.source != WORKING_TREE_SOURCE:
            raise ValueError("change identity source must be working_tree")
        if (
            not isinstance(self.fingerprint, str)
            or len(self.fingerprint) != 64
            or any(character not in "0123456789abcdef" for character in self.fingerprint)
        ):
            raise ValueError("change fingerprint must be 64 lowercase hexadecimal characters")

    def to_json_dict(self) -> dict[str, str]:
        return {"source": self.source, "fingerprint": self.fingerprint}


@dataclass(frozen=True, slots=True)
class ChangedFile:
    path: str
    previous_path: str | None
    staged_status: str | None
    worktree_status: str | None
    untracked: bool
    categories: tuple[str, ...]

    def __post_init__(self) -> None:
        _required_text(self.path, "changed file path")
        if self.previous_path is not None:
            _required_text(self.previous_path, "changed file previous path")
        for label, status in (
            ("staged_status", self.staged_status),
            ("worktree_status", self.worktree_status),
        ):
            if status is not None and status not in _CHANGE_STATUSES:
                raise ValueError(f"{label} is not a supported change status")
        if not self.categories or any(
            category not in _CHANGE_CATEGORIES for category in self.categories
        ):
            raise ValueError("changed file categories must use supported values")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "previous_path": self.previous_path,
            "staged_status": self.staged_status,
            "worktree_status": self.worktree_status,
            "untracked": self.untracked,
            "categories": list(self.categories),
        }


@dataclass(frozen=True, slots=True)
class ChangeImpactSummary:
    total_files: int
    source_files: int
    test_files: int
    contract_files: int
    documentation_files: int
    configuration_files: int
    policy_files: int
    other_files: int

    def __post_init__(self) -> None:
        for name in (
            "total_files",
            "source_files",
            "test_files",
            "contract_files",
            "documentation_files",
            "configuration_files",
            "policy_files",
            "other_files",
        ):
            _non_negative(getattr(self, name), name)

    def to_json_dict(self) -> dict[str, int]:
        return {
            "total_files": self.total_files,
            "source_files": self.source_files,
            "test_files": self.test_files,
            "contract_files": self.contract_files,
            "documentation_files": self.documentation_files,
            "configuration_files": self.configuration_files,
            "policy_files": self.policy_files,
            "other_files": self.other_files,
        }


@dataclass(frozen=True, slots=True)
class ChangeUnknown:
    code: str
    reason: str

    def __post_init__(self) -> None:
        _required_text(self.code, "change unknown code")
        _required_text(self.reason, "change unknown reason")

    def to_json_dict(self) -> dict[str, str]:
        return {"code": self.code, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class InspectChangeResponse:
    available: bool
    project_path: str
    repository_root: str | None
    change: ChangeIdentity
    changed_files: tuple[ChangedFile, ...]
    affected_scopes: tuple[str, ...]
    changed_tests: tuple[str, ...]
    contract_paths: tuple[str, ...]
    documentation_paths: tuple[str, ...]
    configuration_paths: tuple[str, ...]
    policy_paths: tuple[str, ...]
    impact_summary: ChangeImpactSummary
    diagnostics: tuple[Mapping[str, str], ...]
    unknowns: tuple[ChangeUnknown, ...]
    confidence: str
    truncated: bool
    schema_version: int = INSPECT_CHANGE_SCHEMA_VERSION
    tool: str = INSPECT_CHANGE_TOOL
    source: str = WORKING_TREE_SOURCE

    def __post_init__(self) -> None:
        if self.schema_version != INSPECT_CHANGE_SCHEMA_VERSION:
            raise ValueError("inspect_change schema_version must be 1")
        if self.tool != INSPECT_CHANGE_TOOL:
            raise ValueError("inspect_change tool identity is fixed")
        if self.source != WORKING_TREE_SOURCE:
            raise ValueError("inspect_change source must be working_tree")
        _required_text(self.project_path, "inspect change project path")
        if self.repository_root is not None:
            _required_text(self.repository_root, "inspect change repository root")
        if self.confidence not in _CONFIDENCE_VALUES:
            raise ValueError("inspect_change confidence must be high, medium, or low")
        for diagnostic in self.diagnostics:
            _required_text(str(diagnostic.get("code", "")), "diagnostic code")
            _required_text(str(diagnostic.get("message", "")), "diagnostic message")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool": self.tool,
            "source": self.source,
            "available": self.available,
            "project_path": self.project_path,
            "repository_root": self.repository_root,
            "change": self.change.to_json_dict(),
            "changed_files": [item.to_json_dict() for item in self.changed_files],
            "affected_scopes": list(self.affected_scopes),
            "changed_tests": list(self.changed_tests),
            "contract_paths": list(self.contract_paths),
            "documentation_paths": list(self.documentation_paths),
            "configuration_paths": list(self.configuration_paths),
            "policy_paths": list(self.policy_paths),
            "impact_summary": self.impact_summary.to_json_dict(),
            "diagnostics": [dict(item) for item in self.diagnostics],
            "unknowns": [item.to_json_dict() for item in self.unknowns],
            "confidence": self.confidence,
            "truncated": self.truncated,
        }


__all__ = [
    "ChangeIdentity",
    "ChangeImpactSummary",
    "ChangeUnknown",
    "ChangedFile",
    "INSPECT_CHANGE_SCHEMA_VERSION",
    "INSPECT_CHANGE_TOOL",
    "InspectChangeRequest",
    "InspectChangeResponse",
    "WORKING_TREE_SOURCE",
]
