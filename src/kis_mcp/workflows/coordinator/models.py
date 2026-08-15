from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


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
    "ReservationAdmissionError",
    "ReservationRequest",
    "ReservationResult",
    "ScopeRevisionRequest",
]
