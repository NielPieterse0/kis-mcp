from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path
from typing import Any

from .change_analysis import AnalyzeChangeRequest
from .change_service import InspectChangeService
from .context_contracts import CodeContextBudget, GetCodeContextRequest
from .contracts import Confidence, InspectProjectRequest
from .git_reader import GitReader
from .impact_contracts import ImpactBudget
from .intelligence import ProjectIntelligenceService
from .read_authority import ReadAuthority
from .service import InspectProjectService
from .settings import DiscoverSettings
from .planning_contracts import (
    ActiveChangeClaim,
    ClaimConflict,
    PlanChangeAffected,
    PlanChangeAuthority,
    PlanChangeGovernance,
    PlanChangePattern,
    PlanChangeRequest,
    PlanChangeResponse,
    PlanChangeSummary,
    PlanChangeUnknown,
    PlanChangeVerification,
)


class PlanChangeService:
    def __init__(
        self,
        *,
        boundary: Path,
        settings: DiscoverSettings,
        max_claims: int | None = None,
        intelligence_service: ProjectIntelligenceService | None = None,
    ) -> None:
        self._boundary = boundary
        self._settings = settings
        self._authority = ReadAuthority(boundary, settings)
        shared_intelligence = intelligence_service or ProjectIntelligenceService(
            boundary=boundary,
            settings=settings,
        )
        self._project = InspectProjectService(
            boundary=boundary,
            settings=settings,
            intelligence_service=shared_intelligence,
        )
        reader = GitReader(authority=self._authority, settings=settings)
        self._change = InspectChangeService(
            reader,
            intelligence_service=shared_intelligence,
        )
        self._max_claims = min(max_claims or settings.limits.max_evidence, settings.limits.max_evidence)

    def plan(self, request: PlanChangeRequest) -> PlanChangeResponse:
        context = self._project.get_code_context(
            GetCodeContextRequest(
                project=request.project,
                task=request.task,
                budget=CodeContextBudget(
                    max_chars=min(request.max_chars, self._settings.limits.max_output_chars),
                    max_files=min(request.max_files, self._settings.limits.max_files),
                    max_symbols=min(request.max_symbols, self._settings.limits.python_max_records),
                    max_relationships=min(request.max_relationships, self._settings.limits.python_max_records),
                ),
            )
        )
        inventory = self._project.inspect(InspectProjectRequest(path=request.project))
        analysis = self._analyze_change(request, context.task_terms)
        changed_paths = (
            ()
            if analysis is None
            else tuple(
                path
                for path in analysis.normalized_change.changed_paths
                if not _is_change_record(path)
            )
        )
        impact = None if analysis is None or not changed_paths else analysis.impact
        planned_paths = changed_paths or tuple(
            item.path
            for item in context.files
            if item.category in {"source", "contract", "configuration", "documentation", "policy"}
        )
        planned_impact_fingerprint = (
            impact.fingerprint if impact is not None else context.fingerprint
        )
        patterns = _repository_patterns(
            context_files=context.files,
            analysis=analysis,
            changed_paths=changed_paths,
        )
        affected_contracts = _affected_support_paths(
            context_files=context.files,
            impact=impact,
            changed_paths=changed_paths,
            category="contract",
        )
        affected_documentation = _affected_support_paths(
            context_files=context.files,
            impact=impact,
            changed_paths=changed_paths,
            category="documentation",
        )
        affected_configuration = _affected_support_paths(
            context_files=context.files,
            impact=impact,
            changed_paths=changed_paths,
            category="configuration",
        )
        affected_policy = _affected_support_paths(
            context_files=context.files,
            impact=impact,
            changed_paths=changed_paths,
            category="policy",
        )

        inventory_instructions = tuple(
            str(item["path"])
            for item in inventory.instructions
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        )
        instructions = tuple(dict.fromkeys((*inventory_instructions, *context.instructions)))
        inventory_docs = inventory.repository_atlas.get("documentation", ())
        documentation = tuple(
            dict.fromkeys(
                (
                    *(item for item in inventory_docs if isinstance(item, str)),
                    *(item.path for item in context.files if item.category == "documentation"),
                )
            )
        )
        impact_tests = () if impact is None else tuple(item.path for item in impact.affected_tests)
        affected_tests = tuple(dict.fromkeys((*context.tests, *impact_tests)))
        if impact is not None:
            verification_ids = tuple(
                item.verification_id for item in impact.verification_handoffs
            )
            handoffs = tuple(item.to_json_dict() for item in impact.verification_handoffs)
            implementation_steps = tuple(
                item.to_json_dict() for item in impact.implementation_steps
            )
        else:
            declarations = inventory.verification.get("declarations", ())
            verification_ids = tuple(
                str(item["id"])
                for item in declarations
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            )
            handoffs = tuple(
                item.to_json_dict()
                for item in inventory.handoffs
                if item.workflow == "run_verification"
            )
            implementation_steps = ()

        branch = getattr(inventory.git, "branch", None)
        claims, claim_unknowns, claims_truncated = self._active_claims(
            request.project,
            current_branch=branch,
        )
        candidate_paths = planned_paths or tuple(item.path for item in context.files)
        conflicts = _claim_conflicts(claims, candidate_paths)
        unknowns = [
            PlanChangeUnknown(code=item.code, reason=item.reason)
            for item in context.unknowns
        ]
        if not changed_paths:
            unknowns.append(
                PlanChangeUnknown(
                    code="NO_CURRENT_CHANGE",
                    reason="No implementation paths are changed; impact guidance is task-context only.",
                )
            )
        elif impact is not None:
            unknowns.extend(
                PlanChangeUnknown(code=item.code, reason=item.reason)
                for item in impact.unknowns
            )
        unknowns.extend(claim_unknowns)
        reasons = set(context.truncation_reasons)
        if impact is not None:
            reasons.update(impact.truncation_reasons)
        if inventory.truncated:
            reasons.update(inventory.truncation_reasons)
        if claims_truncated:
            reasons.add("active_claims")
        risks = tuple(
            ["Another active change owns paths implicated by this plan."]
            if conflicts
            else []
        )
        confidence = (
            Confidence.LOW
            if conflicts
            else Confidence.MEDIUM
            if reasons or analysis is None
            else Confidence.HIGH
        )

        payload = {
            "project": context.project.to_json_dict(),
            "task": request.task,
            "changed_paths": list(changed_paths),
            "planned_paths": list(planned_paths),
            "context_fingerprint": context.fingerprint,
            "planned_impact_fingerprint": planned_impact_fingerprint,
            "patterns": [item.to_json_dict() for item in patterns],
            "affected_support": {
                "contracts": list(affected_contracts),
                "documentation": list(affected_documentation),
                "configuration": list(affected_configuration),
                "policy": list(affected_policy),
            },
            "claims": [item.to_json_dict() for item in claims],
            "conflicts": [item.to_json_dict() for item in conflicts],
            "verification_ids": list(verification_ids),
        }
        return PlanChangeResponse(
            project=context.project,
            task=request.task,
            authority=PlanChangeAuthority(
                instructions=instructions,
                documentation=documentation,
            ),
            change=PlanChangeSummary(
                source=request.source,
                changed_paths=changed_paths,
                planned_paths=planned_paths,
                planned_impact_fingerprint=planned_impact_fingerprint,
            ),
            affected=PlanChangeAffected(
                context_files=tuple(item.path for item in context.files),
                modules=tuple(item.name for item in context.modules),
                symbols=tuple(item.qualified_name for item in context.symbols),
                tests=affected_tests,
                contracts=affected_contracts,
                documentation=affected_documentation,
                configuration=affected_configuration,
                policy=affected_policy,
            ),
            verification=PlanChangeVerification(ids=verification_ids, handoffs=handoffs),
            implementation_steps=implementation_steps,
            patterns=patterns,
            governance=PlanChangeGovernance(active_claims=claims, conflicts=conflicts),
            risks=risks,
            unknowns=tuple(_dedupe_unknowns(unknowns)),
            confidence=confidence,
            truncated=bool(reasons),
            truncation_reasons=tuple(sorted(reasons)),
            fingerprint=_fingerprint(payload),
        )

    def _analyze_change(self, request: PlanChangeRequest, task_terms: tuple[str, ...]):
        try:
            return self._change.analyze(
                AnalyzeChangeRequest(
                    project=request.project,
                    source=request.source,
                    commit_ref=request.commit_ref,
                    base_ref=request.base_ref,
                    head_ref=request.head_ref,
                    task_terms=task_terms,
                    budget=ImpactBudget(
                        max_symbols=min(request.max_symbols, self._settings.limits.python_max_records),
                        max_dependants=min(request.max_dependants, self._settings.limits.python_max_records),
                        max_tests=min(request.max_tests, self._settings.limits.max_files),
                        max_verifications=min(request.max_verifications, self._settings.limits.max_evidence),
                    ),
                )
            )
        except ValueError as exc:
            if "requires at least one changed path" not in str(exc):
                raise
            return None

    def _active_claims(
        self,
        project: str,
        *,
        current_branch: str | None,
    ) -> tuple[tuple[ActiveChangeClaim, ...], tuple[PlanChangeUnknown, ...], bool]:
        identity = self._authority.resolve_project(project)
        root = Path(identity.canonical_path)
        changes = root / ".work" / "changes"
        if not changes.is_dir():
            return (), (), False
        scope_paths = sorted(
            (
                item / "scope.json"
                for item in changes.iterdir()
                if item.is_dir() and not item.is_symlink() and (item / "scope.json").exists()
            ),
            key=lambda item: item.parent.name.casefold(),
        )
        truncated = len(scope_paths) > self._max_claims
        claims: list[ActiveChangeClaim] = []
        unknowns: list[PlanChangeUnknown] = []
        for scope_path in scope_paths[: self._max_claims]:
            label = scope_path.relative_to(root).as_posix()
            try:
                raw = self._authority.read_relative_text(
                    project,
                    label,
                    max_bytes=self._settings.limits.max_file_bytes,
                ).content
                data = json.loads(raw)
            except Exception:
                unknowns.append(
                    PlanChangeUnknown(
                        code="ACTIVE_CLAIM_UNREADABLE",
                        reason=f"Active change claim could not be parsed: {label}.",
                    )
                )
                continue
            if not isinstance(data, dict) or data.get("status") != "active":
                continue
            branch = data.get("branch") if isinstance(data.get("branch"), str) else None
            if current_branch and branch == current_branch:
                continue
            change_id = data.get("change_id")
            owned = data.get("owned_paths", ())
            shared = data.get("shared_paths", ())
            if not isinstance(change_id, str) or not isinstance(owned, list):
                unknowns.append(
                    PlanChangeUnknown(
                        code="ACTIVE_CLAIM_INVALID",
                        reason=f"Active change claim has invalid required fields: {label}.",
                    )
                )
                continue
            claims.append(
                ActiveChangeClaim(
                    change_id=change_id,
                    status="active",
                    owned_paths=tuple(item for item in owned if isinstance(item, str)),
                    shared_paths=tuple(item for item in shared if isinstance(item, str))
                    if isinstance(shared, list)
                    else (),
                    branch=branch,
                )
            )
        return tuple(claims), tuple(unknowns), truncated


def _affected_support_paths(
    *,
    context_files,
    impact,
    changed_paths: tuple[str, ...],
    category: str,
) -> tuple[str, ...]:
    values: list[str] = [
        item.path for item in context_files if item.category == category
    ]
    values.extend(
        path for path in changed_paths if _plan_path_category(path) == category
    )
    if impact is not None:
        kind = f"{category}_reference"
        for relationship in impact.relationship_impacts:
            if relationship.kind != kind:
                continue
            for path in (relationship.source_path, relationship.target_path):
                if _plan_path_category(path) == category:
                    values.append(path)
    return tuple(dict.fromkeys(values))


def _repository_patterns(
    *,
    context_files,
    analysis,
    changed_paths: tuple[str, ...],
) -> tuple[PlanChangePattern, ...]:
    source_context = tuple(
        item.path for item in context_files if item.category == "source"
    )
    replacement_paths: dict[str, str] = {}
    renamed_destinations: set[str] = set()
    added_paths: set[str] = set()
    if analysis is not None and analysis.change is not None:
        for item in analysis.change.changed_files:
            staged_status = item.staged_status
            worktree_status = item.worktree_status
            statuses = {staged_status, worktree_status}
            if "renamed" in statuses and item.previous_path:
                replacement_paths[item.previous_path] = "renamed"
                renamed_destinations.add(item.path)
            elif "deleted" in statuses:
                replacement_paths[item.path] = "deleted"
            elif "added" in statuses:
                added_paths.add(item.path)

    patterns: list[PlanChangePattern] = [
        PlanChangePattern(
            classification="REPLACE",
            path=path,
            reason="The current change removes or renames an implementation path; reconcile consumers and replacement evidence.",
            confidence=Confidence.HIGH,
        )
        for path in sorted(replacement_paths, key=lambda value: (value.casefold(), value))
        if _is_likely_source_path(path)
    ]
    changed_set = set(changed_paths)
    replacement_set = set(replacement_paths)
    for path in changed_paths:
        if path in replacement_set or path in renamed_destinations:
            continue
        if path not in source_context and not _is_likely_source_path(path):
            continue
        if path in added_paths:
            patterns.append(
                PlanChangePattern(
                    classification="NEW",
                    path=path,
                    reason="The current change adds a new implementation path rather than modifying an existing repository path.",
                    confidence=Confidence.HIGH,
                )
            )
            continue
        patterns.append(
            PlanChangePattern(
                classification="EXTEND",
                path=path,
                reason="The current change modifies an implementation path that already exists in repository evidence.",
                confidence=Confidence.HIGH,
            )
        )
    for path in source_context:
        if path in changed_set or path in replacement_set:
            continue
        patterns.append(
            PlanChangePattern(
                classification="REUSE",
                path=path,
                reason="Task-scoped repository evidence already contains a relevant implementation pattern to reuse or extend.",
                confidence=Confidence.MEDIUM,
            )
        )
    if not patterns:
        patterns.append(
            PlanChangePattern(
                classification="NEW",
                path=None,
                reason="No task-relevant implementation path was found in the bounded repository context; new implementation may be required.",
                confidence=Confidence.LOW,
            )
        )
    return tuple(patterns)


def _is_likely_source_path(path: str) -> bool:
    lowered = path.replace("\\", "/").casefold()
    name = lowered.rsplit("/", 1)[-1]
    if lowered.startswith(("tests/", "test/")) or name.startswith("test_"):
        return False
    if lowered.startswith(("docs/", "settings/", "config/", "contracts/", "policy/")):
        return False
    return lowered.startswith("src/") or name.endswith(
        (".py", ".js", ".jsx", ".ts", ".tsx", ".cs", ".go", ".rs", ".java", ".kt")
    )


def _plan_path_category(path: str) -> str:
    lowered = path.replace("\\", "/").casefold()
    name = lowered.rsplit("/", 1)[-1]
    if lowered.startswith(("contracts/", "contract/", "schemas/", "schema/")) or name.endswith(".schema.json"):
        return "contract"
    if lowered.startswith(("policy/", "policies/")) or name.startswith("policy."):
        return "policy"
    if lowered.startswith(("settings/", "config/", "configs/", ".github/")) or name.endswith((".toml", ".yaml", ".yml", ".ini")):
        return "configuration"
    if lowered.startswith(("docs/", "doc/")) or name.endswith((".md", ".rst")):
        return "documentation"
    return "source" if _is_likely_source_path(path) else "other"


def _claim_conflicts(
    claims: tuple[ActiveChangeClaim, ...],
    candidate_paths: tuple[str, ...],
) -> tuple[ClaimConflict, ...]:
    results: list[ClaimConflict] = []
    for claim in claims:
        paths = tuple(
            path
            for path in candidate_paths
            if any(_matches(path, pattern) for pattern in claim.owned_paths)
        )
        if paths:
            results.append(ClaimConflict(change_id=claim.change_id, paths=paths))
    return tuple(results)


def _is_change_record(path: str) -> bool:
    normalized = path.replace("\\", "/").casefold().strip("/")
    return normalized.startswith(".work/changes/")


def _matches(path: str, pattern: str) -> bool:
    normalized_path = path.replace("\\", "/").strip("/")
    normalized_pattern = pattern.replace("\\", "/").strip("/")
    if normalized_pattern.endswith("/**"):
        prefix = normalized_pattern[:-3].rstrip("/")
        return normalized_path == prefix or normalized_path.startswith(f"{prefix}/")
    return fnmatch.fnmatchcase(normalized_path, normalized_pattern)


def _dedupe_unknowns(values: list[PlanChangeUnknown]) -> list[PlanChangeUnknown]:
    unique = {(item.code, item.reason): item for item in values}
    return [unique[key] for key in sorted(unique)]


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = ["PlanChangeService"]
