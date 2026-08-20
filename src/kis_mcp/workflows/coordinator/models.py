from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence


_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ReservationAdmissionError(RuntimeError):
    def __init__(self, code: str, reason: str) -> None:
        self.code = code
        self.reason = reason
        super().__init__(f"{code}: {reason}")


@dataclass(frozen=True, slots=True)
class ReservationRequest:
    project_id: str
    slug: str
    outcome: str
    owned_paths: tuple[str, ...]
    shared_paths: tuple[str, ...] = ()
    excluded_paths: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    integration_owner: str | None = None
    work_management: Mapping[str, Any] | None = None
    complexity: str = "medium"
    risk_triggers: tuple[str, ...] = ()
    base: str = "main"

    def __post_init__(self) -> None:
        for label, value in (
            ("project_id", self.project_id),
            ("slug", self.slug),
            ("outcome", self.outcome),
            ("base", self.base),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} must be a non-empty string")
        if _SLUG_PATTERN.fullmatch(self.slug) is None:
            raise ValueError("slug must be lower-case kebab-case")
        if self.complexity not in {"small", "medium", "large"}:
            raise ValueError("complexity must be small, medium, or large")
        if tuple(sorted(set(self.risk_triggers))) != self.risk_triggers:
            raise ValueError("risk_triggers must be unique and sorted")
        for field_name, values in (
            ("owned_paths", self.owned_paths),
            ("shared_paths", self.shared_paths),
            ("excluded_paths", self.excluded_paths),
            ("dependencies", self.dependencies),
        ):
            if len(set(values)) != len(values) or any(not item.strip() for item in values):
                raise ValueError(f"{field_name} must contain unique non-empty strings")
        if not self.owned_paths and not self.shared_paths:
            raise ValueError("at least one owned or shared path is required")
        if self.integration_owner is not None and not self.integration_owner.strip():
            raise ValueError("integration_owner must be non-empty when supplied")


@dataclass(frozen=True, slots=True)
class ScopeRevisionRequest:
    request_id: str
    reservation_id: str
    expected_authority_revision: int
    expected_fence_token: int
    add_owned_paths: tuple[str, ...] = ()
    remove_owned_paths: tuple[str, ...] = ()
    add_shared_paths: tuple[str, ...] = ()
    remove_shared_paths: tuple[str, ...] = ()
    add_dependencies: tuple[str, ...] = ()
    remove_dependencies: tuple[str, ...] = ()
    integration_owner: str | None = None

    def __post_init__(self) -> None:
        if not self.request_id.strip() or not self.reservation_id.strip():
            raise ValueError("request_id and reservation_id are required")
        if self.expected_authority_revision < 1 or self.expected_fence_token < 1:
            raise ValueError("expected authority revision and fence token must be positive")
        changed = False
        for field_name, values in (
            ("add_owned_paths", self.add_owned_paths),
            ("remove_owned_paths", self.remove_owned_paths),
            ("add_shared_paths", self.add_shared_paths),
            ("remove_shared_paths", self.remove_shared_paths),
            ("add_dependencies", self.add_dependencies),
            ("remove_dependencies", self.remove_dependencies),
        ):
            if len(set(values)) != len(values) or any(not item.strip() for item in values):
                raise ValueError(f"{field_name} must contain unique non-empty strings")
            changed = changed or bool(values)
        for add, remove, field_name in (
            (self.add_owned_paths, self.remove_owned_paths, "owned_paths"),
            (self.add_shared_paths, self.remove_shared_paths, "shared_paths"),
            (self.add_dependencies, self.remove_dependencies, "dependencies"),
        ):
            if set(add) & set(remove):
                raise ValueError(f"{field_name} cannot add and remove the same value")
        if self.integration_owner is not None:
            if not self.integration_owner.strip():
                raise ValueError("integration_owner must be non-empty when supplied")
            changed = True
        if not changed:
            raise ValueError("scope revision must change at least one authority field")


@dataclass(frozen=True, slots=True)
class PlannerTask:
    task_id: str
    outcome: str
    owned_paths: tuple[str, ...]
    acceptance_checks: tuple[str, ...]
    shared_paths: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    integration_owner: str | None = None
    kind: str = "task"

    def __post_init__(self) -> None:
        for label, value in (("task_id", self.task_id), ("outcome", self.outcome)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} must be a non-empty string")
        for field_name in (
            "owned_paths",
            "shared_paths",
            "dependencies",
            "acceptance_checks",
            "required_capabilities",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, Sequence) or isinstance(
                values, (str, bytes, bytearray)
            ):
                raise ValueError(f"{field_name} must be a sequence of strings")
            object.__setattr__(self, field_name, tuple(values))
        if self.kind not in {"change", "slice", "task"}:
            raise ValueError("kind must be change, slice, or task")
        for field_name, values in (
            ("owned_paths", self.owned_paths),
            ("shared_paths", self.shared_paths),
            ("dependencies", self.dependencies),
            ("acceptance_checks", self.acceptance_checks),
            ("required_capabilities", self.required_capabilities),
        ):
            if len(set(values)) != len(values) or any(
                not isinstance(item, str) or not item.strip() for item in values
            ):
                raise ValueError(f"{field_name} must contain unique non-empty strings")
        if not self.owned_paths and not self.shared_paths:
            raise ValueError("planner task requires at least one owned or shared path")
        if not self.acceptance_checks:
            raise ValueError("planner task requires at least one acceptance check")
        if self.integration_owner is not None and (
            not isinstance(self.integration_owner, str) or not self.integration_owner.strip()
        ):
            raise ValueError("integration_owner must be a non-empty string when supplied")


@dataclass(frozen=True, slots=True)
class PlannerRequest:
    project_id: str
    change_id: str
    work_id: str
    slice_id: str
    revision: int
    exact_base: Mapping[str, str]
    tasks: tuple[PlannerTask, ...]
    governed_root: str = "."
    governed_worktree: str = "."
    lifecycle_phase: str = "implementation"
    authority_references: tuple[str, ...] = ()
    work_management: Mapping[str, Any] | None = None
    external_provenance: Mapping[str, Any] | None = None
    verification_requirement_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for label, value in (
            ("project_id", self.project_id),
            ("change_id", self.change_id),
            ("work_id", self.work_id),
            ("slice_id", self.slice_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} must be a non-empty string")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ValueError("revision must be a positive integer")
        for label in ("governed_root", "governed_worktree", "lifecycle_phase"):
            value = getattr(self, label)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} must be a non-empty string")
        object.__setattr__(self, "exact_base", MappingProxyType(dict(self.exact_base)))
        object.__setattr__(self, "authority_references", tuple(self.authority_references))
        if len(set(self.authority_references)) != len(self.authority_references) or any(
            not isinstance(item, str) or not item.strip() for item in self.authority_references
        ):
            raise ValueError("authority_references must contain unique non-empty strings")
        for label in ("work_management", "external_provenance"):
            value = getattr(self, label)
            if value is not None:
                if not isinstance(value, Mapping):
                    raise ValueError(f"{label} must be an object when supplied")
                object.__setattr__(self, label, MappingProxyType(dict(value)))
        if not isinstance(self.tasks, Sequence) or isinstance(
            self.tasks, (str, bytes, bytearray)
        ):
            raise ValueError("tasks must be a sequence of PlannerTask values")
        object.__setattr__(self, "tasks", tuple(self.tasks))
        if not isinstance(self.verification_requirement_ids, Sequence) or isinstance(
            self.verification_requirement_ids, (str, bytes, bytearray)
        ):
            raise ValueError("verification_requirement_ids must be a sequence of strings")
        object.__setattr__(
            self,
            "verification_requirement_ids",
            tuple(self.verification_requirement_ids),
        )
        if not self.tasks:
            raise ValueError("planner request requires at least one task")
        if any(not isinstance(task, PlannerTask) for task in self.tasks):
            raise ValueError("tasks must contain only PlannerTask values")
        if len({task.task_id for task in self.tasks}) != len(self.tasks):
            raise ValueError("planner task IDs must be unique")
        if len(set(self.verification_requirement_ids)) != len(self.verification_requirement_ids):
            raise ValueError("verification_requirement_ids must be unique")
        if any(
            not isinstance(item, str) or not item.strip()
            for item in self.verification_requirement_ids
        ):
            raise ValueError("verification_requirement_ids must be non-empty strings")


@dataclass(frozen=True, slots=True)
class ReservationResult:
    reservation: Mapping[str, Any]
    work_packet_identity: Mapping[str, Any]
    branch: str
    worktree: str
    status: str = "reserved"
    work_management_claim: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status != "reserved":
            raise ValueError("reservation result status is fixed to reserved")
        if not self.branch.strip() or not self.worktree.strip():
            raise ValueError("reservation branch and worktree are required")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reservation": dict(self.reservation),
            "work_packet_identity": dict(self.work_packet_identity),
            "branch": self.branch,
            "worktree": self.worktree,
            "work_management_claim": (
                dict(self.work_management_claim)
                if self.work_management_claim is not None
                else None
            ),
        }


__all__ = [
    "PlannerRequest",
    "PlannerTask",
    "ReservationAdmissionError",
    "ReservationRequest",
    "ReservationResult",
    "ScopeRevisionRequest",
]
