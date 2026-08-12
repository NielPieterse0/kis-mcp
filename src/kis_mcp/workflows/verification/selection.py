from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from ...discover.change_analysis import AnalyzeChangeRequest
from ...discover.contracts import InspectProjectRequest
from ...discover.impact_contracts import ImpactBudget
from .contracts import (
    VerificationSelectionIssue,
    VerificationSelectionItem,
    VerificationSelectionResult,
)
from .execution import SUPPORTED_VERIFICATION_PROFILES

_CATEGORY_PRIORITY = {
    "repository_verification": 0,
    "test": 1,
    "lint": 2,
    "typecheck": 3,
    "dependency": 4,
    "documentation": 5,
}


class AnalyzeChangePort(Protocol):
    def analyze(self, request: AnalyzeChangeRequest) -> Any: ...


class InspectProjectPort(Protocol):
    def inspect(self, request: InspectProjectRequest) -> Any: ...


class VerificationSelectionError(ValueError):
    def __init__(self, code: str, reason: str) -> None:
        self.code = code
        self.reason = reason
        super().__init__(f"{code}: {reason}")


class VerificationSelectionService:
    def __init__(self, *, analyzer: AnalyzeChangePort, inspector: InspectProjectPort) -> None:
        self._analyzer = analyzer
        self._inspector = inspector

    def select(
        self,
        *,
        project: str,
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
        task_terms: tuple[str, ...] = (),
        max_verifications: int = 20,
    ) -> VerificationSelectionResult:
        project = _required(project, "project")
        if isinstance(max_verifications, bool) or not isinstance(max_verifications, int):
            raise VerificationSelectionError(
                "VERIFICATION_SELECTION_LIMIT_INVALID",
                "max_verifications must be a positive integer no greater than 50.",
            )
        if max_verifications < 1 or max_verifications > 50:
            raise VerificationSelectionError(
                "VERIFICATION_SELECTION_LIMIT_INVALID",
                "max_verifications must be a positive integer no greater than 50.",
            )
        analysis = self._analyzer.analyze(
            AnalyzeChangeRequest(
                project=project,
                source=source,
                commit_ref=commit_ref,
                base_ref=base_ref,
                head_ref=head_ref,
                task_terms=task_terms,
                budget=ImpactBudget(
                    max_symbols=100,
                    max_dependants=100,
                    max_tests=100,
                    max_verifications=50,
                ),
            )
        )
        inspection = self._inspector.inspect(InspectProjectRequest(path=project))
        declarations = _declarations_by_id(inspection.verification)
        selected: list[VerificationSelectionItem] = []
        skipped: list[VerificationSelectionIssue] = []
        seen: set[str] = set()

        for handoff in analysis.impact.verification_handoffs:
            verification_id = str(handoff.verification_id)
            if verification_id in seen:
                continue
            seen.add(verification_id)
            declaration = declarations.get(verification_id)
            issue = _selection_issue(handoff, declaration)
            if issue is not None:
                skipped.append(issue)
                continue
            selected.append(
                VerificationSelectionItem(
                    verification_id=verification_id,
                    category=str(handoff.category),
                    reason=str(handoff.reason),
                    profile=str(handoff.profile),
                    source_path=str(handoff.source_path),
                )
            )

        selected.sort(key=_selection_sort_key)
        skipped.sort(key=lambda item: (item.verification_id.casefold(), item.code))
        selection_omitted = max(0, len(selected) - max_verifications)
        if selection_omitted:
            selected = selected[:max_verifications]
        impact_omissions = getattr(analysis.impact, "omissions", None)
        impact_omitted = getattr(impact_omissions, "verifications", 0)
        omitted_count = selection_omitted + (
            impact_omitted if isinstance(impact_omitted, int) and impact_omitted > 0 else 0
        )
        impact_truncated = bool(getattr(analysis.impact, "truncated", False))
        return VerificationSelectionResult(
            project=project,
            source_fingerprint=str(analysis.impact.fingerprint),
            selected=tuple(selected),
            skipped=tuple(skipped),
            omitted_count=omitted_count,
            truncated=impact_truncated or bool(omitted_count),
        )


def _declarations_by_id(verification: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = verification.get("declarations", ())
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        return {}
    return {
        str(item["id"]): item
        for item in raw
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    }


def _selection_issue(handoff: Any, declaration: Mapping[str, Any] | None) -> VerificationSelectionIssue | None:
    verification_id = str(handoff.verification_id)
    if declaration is None:
        return VerificationSelectionIssue(
            verification_id=verification_id,
            code="VERIFICATION_SELECTION_DECLARATION_MISSING",
            reason="The Discover handoff no longer has a current project declaration.",
        )
    profile = str(declaration.get("profile", ""))
    if profile not in SUPPORTED_VERIFICATION_PROFILES:
        return VerificationSelectionIssue(
            verification_id=verification_id,
            code="VERIFICATION_SELECTION_PROFILE_UNSUPPORTED",
            reason=f"Work does not execute verification profile {profile!r}.",
        )
    if not _handoff_matches_declaration(handoff, declaration):
        return VerificationSelectionIssue(
            verification_id=verification_id,
            code="VERIFICATION_SELECTION_HANDOFF_STALE",
            reason="The Discover handoff does not match the current verification declaration.",
        )
    return None


def _handoff_matches_declaration(handoff: Any, declaration: Mapping[str, Any]) -> bool:
    arguments = declaration.get("arguments", ())
    if not isinstance(arguments, Sequence) or isinstance(arguments, (str, bytes, bytearray)):
        return False
    return (
        declaration.get("profile") == handoff.profile
        and tuple(arguments) == tuple(handoff.arguments)
        and declaration.get("category") == handoff.category
        and declaration.get("source_path") == handoff.source_path
    )


def _selection_sort_key(item: VerificationSelectionItem) -> tuple[int, str]:
    return (
        _CATEGORY_PRIORITY.get(item.category, 99),
        item.verification_id.casefold(),
    )


def _required(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VerificationSelectionError(
            "VERIFICATION_SELECTION_REQUEST_INVALID",
            f"{label} must be a non-empty string.",
        )
    return value.strip()


__all__ = [
    "AnalyzeChangePort",
    "InspectProjectPort",
    "VerificationSelectionError",
    "VerificationSelectionService",
]
