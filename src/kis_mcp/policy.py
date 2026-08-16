from __future__ import annotations

from dataclasses import dataclass

from .models import DecisionKind, InvocationEffects, PolicyDecision
from .paths import (
    PathValidationError,
    is_within_windows_boundary,
    normalize_windows_path,
    resolve_windows_effective_path,
)


@dataclass(frozen=True, slots=True)
class ThreeRulePolicy:
    project_boundary: str
    quarantine_root: str

    def __post_init__(self) -> None:
        normalized_boundary = normalize_windows_path(
            self.project_boundary, base=self.project_boundary
        )
        normalized_quarantine = resolve_windows_effective_path(
            self.quarantine_root,
            base=normalized_boundary,
            follow_final=False,
        )
        if not is_within_windows_boundary(
            normalized_quarantine, boundary=normalized_boundary
        ):
            raise ValueError("Quarantine root must be inside the project boundary")
        object.__setattr__(self, "project_boundary", normalized_boundary)
        object.__setattr__(
            self,
            "quarantine_root",
            normalize_windows_path(self.quarantine_root, base=normalized_boundary),
        )

    def evaluate(self, effects: InvocationEffects) -> PolicyDecision:
        external_paths: list[str] = []
        valid_delete_paths: list[str] = []
        unresolved_mutation_paths: list[str] = [
            *effects.unresolved_write_paths,
            *effects.unresolved_entry_paths,
            *effects.unresolved_delete_paths,
        ]

        for path in effects.write_paths:
            try:
                effective = resolve_windows_effective_path(
                    path,
                    base=self.project_boundary,
                    follow_final=True,
                )
            except PathValidationError:
                # A syntactically identified write target that cannot be validated is
                # a structural invocation error, not evidence of HR-001.
                unresolved_mutation_paths.append(path)
                continue
            if not is_within_windows_boundary(
                effective, boundary=self.project_boundary
            ):
                external_paths.append(effective)

        for path in effects.entry_paths:
            try:
                effective = resolve_windows_effective_path(
                    path,
                    base=self.project_boundary,
                    follow_final=False,
                )
            except PathValidationError:
                # The entry mutation is definite even when its path cannot be bounded;
                # reject it structurally without attributing HR-001.
                unresolved_mutation_paths.append(path)
                continue
            if not is_within_windows_boundary(
                effective, boundary=self.project_boundary
            ):
                external_paths.append(effective)

        for path in effects.delete_paths:
            try:
                effective = resolve_windows_effective_path(
                    path,
                    base=self.project_boundary,
                    follow_final=False,
                )
                normalized = normalize_windows_path(path, base=self.project_boundary)
            except PathValidationError:
                unresolved_mutation_paths.append(path)
                continue
            if not is_within_windows_boundary(
                effective, boundary=self.project_boundary
            ):
                external_paths.append(effective)
            else:
                valid_delete_paths.append(normalized)

        if unresolved_mutation_paths:
            return PolicyDecision(
                kind=DecisionKind.BLOCK,
                code="INVALID_INVOCATION_PATH",
                message=(
                    "A definite mutation target could not be resolved into a path that "
                    "can be validated safely against the project boundary."
                ),
                paths=tuple(dict.fromkeys(unresolved_mutation_paths)),
            )

        if external_paths:
            return PolicyDecision(
                kind=DecisionKind.BLOCK,
                rule_id="HR-001",
                code="HR-001_WRITE_OUTSIDE_PROJECTS",
                message=(
                    "The invocation would modify a path outside the approved "
                    f"boundary {self.project_boundary}."
                ),
                paths=tuple(dict.fromkeys(external_paths)),
            )

        if effects.external_network:
            return PolicyDecision(
                kind=DecisionKind.BLOCK,
                rule_id="HR-002",
                code="HR-002_EXTERNAL_NETWORK",
                message=(
                    "External network access is not available through the local "
                    "Work path. Use an approved connector or an explicit "
                    "operator-supervised action outside Work."
                ),
            )

        if effects.unresolved_delete:
            return PolicyDecision(
                kind=DecisionKind.BLOCK,
                rule_id="HR-003",
                code="HR-003_QUARANTINE_REQUIRED",
                message=(
                    "The invocation definitely requests permanent deletion, but its "
                    "exact targets cannot be transformed safely into quarantine."
                ),
            )

        if valid_delete_paths:
            normalized_deletes = tuple(dict.fromkeys(valid_delete_paths))
            if any(
                normalized.casefold() == self.project_boundary.casefold()
                for normalized in normalized_deletes
            ):
                return PolicyDecision(
                    kind=DecisionKind.BLOCK,
                    rule_id="HR-003",
                    code="HR-003_QUARANTINE_FAILED",
                    message="The approved project boundary itself cannot be quarantined.",
                    paths=normalized_deletes,
                )
            return PolicyDecision(
                kind=DecisionKind.QUARANTINE,
                rule_id="HR-003",
                code="HR-003_QUARANTINE_REQUIRED",
                message="Permanent deletion is replaced with recoverable quarantine.",
                paths=normalized_deletes,
            )

        return PolicyDecision(
            kind=DecisionKind.ALLOW,
            code="ALLOW",
            message="The invocation does not resolve to a prohibited outcome.",
        )
