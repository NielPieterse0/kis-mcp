from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


INSPECT_CHANGE_SCHEMA_VERSION = 1
INSPECT_CHANGE_TOOL = "inspect_change"
WORKING_TREE_SOURCE = "working_tree"
SUPPORTED_CHANGE_SOURCES = frozenset(
    {WORKING_TREE_SOURCE, "staged", "commit", "range", "branch"}
)

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
_REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@+\-]*$")


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _non_negative(value: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _validated_ref(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    _required_text(value, label)
    if len(value) > 255:
        raise ValueError(f"{label} exceeds 255 characters")
    if value.startswith("-"):
        raise ValueError(f"{label} must not be option-like")
    if not _REF_PATTERN.fullmatch(value):
        raise ValueError(f"{label} contains unsupported characters")
    if any(marker in value for marker in ("..", "@{", "//")):
        raise ValueError(f"{label} contains an unsafe Git ref sequence")
    if value.startswith(".") or value.endswith((".", "/")):
        raise ValueError(f"{label} has an invalid Git ref boundary")
    return value


def _validate_target_shape(
    source: str,
    *,
    commit_ref: str | None,
    base_ref: str | None,
    head_ref: str | None,
) -> None:
    if source not in SUPPORTED_CHANGE_SOURCES:
        raise ValueError("inspect change source is unsupported")
    if source in {WORKING_TREE_SOURCE, "staged"}:
        if any(value is not None for value in (commit_ref, base_ref, head_ref)):
            raise ValueError(f"{source} source does not accept target refs")
        return
    if source == "commit":
        if commit_ref is None:
            raise ValueError("commit source requires commit_ref")
        if base_ref is not None or head_ref is not None:
            raise ValueError("commit source accepts only commit_ref")
        return
    if commit_ref is not None:
        raise ValueError(f"{source} source does not accept commit_ref")
    if base_ref is None or head_ref is None:
        raise ValueError(f"{source} source requires base_ref and head_ref")


@dataclass(frozen=True, slots=True)
class InspectChangeRequest:
    path: str
    source: str = WORKING_TREE_SOURCE
    commit_ref: str | None = None
    base_ref: str | None = None
    head_ref: str | None = None

    def __post_init__(self) -> None:
        _required_text(self.path, "inspect change path")
        _validated_ref(self.commit_ref, "commit_ref")
        _validated_ref(self.base_ref, "base_ref")
        _validated_ref(self.head_ref, "head_ref")
        _validate_target_shape(
            self.source,
            commit_ref=self.commit_ref,
            base_ref=self.base_ref,
            head_ref=self.head_ref,
        )

    def to_json_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"path": self.path, "source": self.source}
        for name in ("commit_ref", "base_ref", "head_ref"):
            value = getattr(self, name)
            if value is not None:
                result[name] = value
        return result


@dataclass(frozen=True, slots=True)
class ChangeIdentity:
    source: str
    fingerprint: str
    commit_ref: str | None = None
    base_ref: str | None = None
    head_ref: str | None = None

    def __post_init__(self) -> None:
        _validated_ref(self.commit_ref, "change commit_ref")
        _validated_ref(self.base_ref, "change base_ref")
        _validated_ref(self.head_ref, "change head_ref")
        _validate_target_shape(
            self.source,
            commit_ref=self.commit_ref,
            base_ref=self.base_ref,
            head_ref=self.head_ref,
        )
        if (
            not isinstance(self.fingerprint, str)
            or len(self.fingerprint) != 64
            or any(character not in "0123456789abcdef" for character in self.fingerprint)
        ):
            raise ValueError("change fingerprint must be 64 lowercase hexadecimal characters")

    def to_json_dict(self) -> dict[str, str]:
        result = {"source": self.source, "fingerprint": self.fingerprint}
        for name in ("commit_ref", "base_ref", "head_ref"):
            value = getattr(self, name)
            if value is not None:
                result[name] = value
        return result


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
class ChangeVerificationHandoff:
    handoff_id: str
    verification_id: str
    category: str
    reason: str
    paths: tuple[str, ...]
    target_plane: str = "work"
    workflow: str = "run_verification"

    def __post_init__(self) -> None:
        for value, label in (
            (self.handoff_id, "change handoff id"),
            (self.verification_id, "change verification id"),
            (self.category, "change verification category"),
            (self.reason, "change verification reason"),
            (self.target_plane, "change handoff target plane"),
            (self.workflow, "change handoff workflow"),
        ):
            _required_text(value, label)
        if self.target_plane != "work" or self.workflow != "run_verification":
            raise ValueError("change verification handoff target is fixed")
        if not self.paths or any(not path.strip() for path in self.paths):
            raise ValueError("change verification handoff paths must be non-empty")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "handoff_id": self.handoff_id,
            "target_plane": self.target_plane,
            "workflow": self.workflow,
            "verification_id": self.verification_id,
            "category": self.category,
            "reason": self.reason,
            "paths": list(self.paths),
        }


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
    verification_handoffs: tuple[ChangeVerificationHandoff, ...] = ()
    schema_version: int = INSPECT_CHANGE_SCHEMA_VERSION
    tool: str = INSPECT_CHANGE_TOOL
    source: str = WORKING_TREE_SOURCE

    def __post_init__(self) -> None:
        if self.schema_version != INSPECT_CHANGE_SCHEMA_VERSION:
            raise ValueError("inspect_change schema_version must be 1")
        if self.tool != INSPECT_CHANGE_TOOL:
            raise ValueError("inspect_change tool identity is fixed")
        if self.source not in SUPPORTED_CHANGE_SOURCES:
            raise ValueError("inspect_change source is unsupported")
        if self.source != self.change.source:
            raise ValueError("inspect_change source must match change identity")
        _required_text(self.project_path, "inspect change project path")
        if self.repository_root is not None:
            _required_text(self.repository_root, "inspect change repository root")
        if self.confidence not in _CONFIDENCE_VALUES:
            raise ValueError("inspect_change confidence must be high, medium, or low")
        for diagnostic in self.diagnostics:
            _required_text(str(diagnostic.get("code", "")), "diagnostic code")
            _required_text(str(diagnostic.get("message", "")), "diagnostic message")

    def to_json_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
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
        if self.verification_handoffs:
            result["verification_handoffs"] = [
                item.to_json_dict() for item in self.verification_handoffs
            ]
        return result


__all__ = [
    "ChangeIdentity",
    "ChangeImpactSummary",
    "ChangeUnknown",
    "ChangeVerificationHandoff",
    "ChangedFile",
    "INSPECT_CHANGE_SCHEMA_VERSION",
    "INSPECT_CHANGE_TOOL",
    "InspectChangeRequest",
    "InspectChangeResponse",
    "SUPPORTED_CHANGE_SOURCES",
    "WORKING_TREE_SOURCE",
]
