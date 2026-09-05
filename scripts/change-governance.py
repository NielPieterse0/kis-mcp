from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


def _load_change_governance_settings() -> dict[str, Any]:
    path = (
        Path(__file__).resolve().parents[1]
        / "settings"
        / "change-governance.settings.json"
    )
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise RuntimeError(
            "CHANGE_GOVERNANCE_SETTINGS_INVALID: schema_version must be 1"
        )
    required = {"schema_version", "complexities", "review_types", "risk_triggers"}
    if set(document) != required:
        raise RuntimeError(
            "CHANGE_GOVERNANCE_SETTINGS_INVALID: unexpected settings keys"
        )
    return document


_CHANGE_GOVERNANCE_SETTINGS = _load_change_governance_settings()
DEFAULT_STATE_ROOT = Path(r"C:\Projects\.kis-mcp")


CHANGE_ID_PATTERN = re.compile(r"^[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")
CHANGE_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PROJECT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
WORK_RECORD_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[0-9]+$")
SOURCE_REPOSITORY_PATTERN = re.compile(r"^[^/\s]+/[^/\s]+$")
ACTIVE_STATUSES = frozenset({"active", "ready"})
ALL_STATUSES = ACTIVE_STATUSES | {"closed"}
DOCUMENTATION_IMPACTS = frozenset(
    {
        "not_assessed",
        "none",
        "planned",
        "in_progress",
        "pre_merge_complete",
        "post_merge_complete",
    }
)
WORK_SOURCE_KINDS = frozenset({"issue", "pull_request"})
LEGACY_RISK_PROFILES = frozenset({"lean", "standard", "rigorous"})
COMPLEXITIES = frozenset(_CHANGE_GOVERNANCE_SETTINGS["complexities"])
RISK_TRIGGERS = frozenset(_CHANGE_GOVERNANCE_SETTINGS["risk_triggers"])
CHANGE_FILES_BY_COMPLEXITY = {
    name: tuple(spec["artifacts"])
    for name, spec in _CHANGE_GOVERNANCE_SETTINGS["complexities"].items()
}
BASE_RELATIONS = frozenset(
    {"same_sha", "tree_equivalent", "content_divergence", "unavailable"}
)
LEGACY_FULL_CHANGE_FILES = (
    "scope.json",
    "spec.md",
    "plan.md",
    "tasks.md",
    "closeout.md",
)
LEGACY_COMPACT_CHANGE_FILES = ("scope.json", "change.md")
TEMPLATE_CHANGE_FILES = tuple(
    dict.fromkeys(
        file_name
        for files in (
            *CHANGE_FILES_BY_COMPLEXITY.values(),
            LEGACY_FULL_CHANGE_FILES,
            LEGACY_COMPACT_CHANGE_FILES,
        )
        for file_name in files
    )
)
REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "change_id",
        "status",
        "branch",
        "worktree",
        "base",
        "outcome",
        "owned_paths",
        "shared_paths",
        "excluded_paths",
        "dependencies",
        "integration_owner",
    }
)


class ClaimError(ValueError):
    """Raised when change governance cannot safely proceed."""


@dataclass(frozen=True, slots=True)
class PathClaim:
    raw: str
    prefix: str
    recursive: bool

    def matches(self, path: str) -> bool:
        normalized = _normalize_repository_path(path)
        if self.recursive:
            return normalized == self.prefix or normalized.startswith(f"{self.prefix}/")
        return normalized == self.prefix

    def overlaps(self, other: "PathClaim") -> bool:
        if not self.recursive and not other.recursive:
            return self.prefix == other.prefix
        if self.recursive and other.recursive:
            return _is_same_or_descendant(
                self.prefix, other.prefix
            ) or _is_same_or_descendant(other.prefix, self.prefix)
        recursive = self if self.recursive else other
        exact = other if self.recursive else self
        return _is_same_or_descendant(exact.prefix, recursive.prefix)


@dataclass(frozen=True, slots=True)
class WorkManagementClaim:
    project_id: str
    record_id: str
    source_repository: str
    source_number: int
    source_kind: str
    documentation_impact: str
    execution_owner: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "WorkManagementClaim":
        required = {
            "project_id",
            "record_id",
            "source_repository",
            "source_number",
            "source_kind",
            "documentation_impact",
        }
        allowed = required | {"execution_owner"}
        missing = sorted(required.difference(data))
        unknown = sorted(set(data).difference(allowed))
        if missing:
            raise ClaimError(f"WORK_MANAGEMENT_FIELDS_MISSING: {', '.join(missing)}")
        if unknown:
            raise ClaimError(f"WORK_MANAGEMENT_FIELDS_UNKNOWN: {', '.join(unknown)}")
        project_id = _require_string(data["project_id"], "work_management.project_id")
        if PROJECT_ID_PATTERN.fullmatch(project_id) is None:
            raise ClaimError(f"WORK_MANAGEMENT_PROJECT_ID_INVALID: {project_id}")
        record_id = _require_string(data["record_id"], "work_management.record_id")
        if WORK_RECORD_ID_PATTERN.fullmatch(record_id) is None:
            raise ClaimError(f"WORK_MANAGEMENT_RECORD_ID_INVALID: {record_id}")
        source_repository = _require_string(
            data["source_repository"], "work_management.source_repository"
        )
        if SOURCE_REPOSITORY_PATTERN.fullmatch(source_repository) is None:
            raise ClaimError(
                f"WORK_MANAGEMENT_SOURCE_REPOSITORY_INVALID: {source_repository}"
            )
        source_number = data["source_number"]
        if (
            isinstance(source_number, bool)
            or not isinstance(source_number, int)
            or source_number <= 0
        ):
            raise ClaimError(
                "WORK_MANAGEMENT_SOURCE_NUMBER_INVALID: expected positive integer"
            )
        source_kind = _require_string(
            data["source_kind"], "work_management.source_kind"
        )
        if source_kind not in WORK_SOURCE_KINDS:
            raise ClaimError(f"WORK_MANAGEMENT_SOURCE_KIND_INVALID: {source_kind}")
        documentation_impact = _require_string(
            data["documentation_impact"], "work_management.documentation_impact"
        )
        if documentation_impact not in DOCUMENTATION_IMPACTS:
            raise ClaimError(
                f"WORK_MANAGEMENT_DOCUMENTATION_IMPACT_INVALID: {documentation_impact}"
            )
        execution_owner = _optional_string(
            data.get("execution_owner"), "work_management.execution_owner"
        )
        return cls(
            project_id=project_id,
            record_id=record_id,
            source_repository=source_repository,
            source_number=source_number,
            source_kind=source_kind,
            documentation_impact=documentation_impact,
            execution_owner=execution_owner,
        )

    def to_mapping(self) -> dict[str, Any]:
        result = {
            "project_id": self.project_id,
            "record_id": self.record_id,
            "source_repository": self.source_repository,
            "source_number": self.source_number,
            "source_kind": self.source_kind,
            "documentation_impact": self.documentation_impact,
        }
        if self.execution_owner is not None:
            result["execution_owner"] = self.execution_owner
        return result


@dataclass(frozen=True, slots=True)
class BaseEvidence:
    local_sha: str
    local_tree: str
    upstream_sha: str | None
    upstream_tree: str | None
    upstream_ref: str | None
    evidence_source: str
    relation: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "BaseEvidence":
        local_sha = _require_sha(data.get("local_sha"), "base_evidence.local_sha")
        local_tree = _require_sha(data.get("local_tree"), "base_evidence.local_tree")
        upstream_sha = _optional_sha(
            data.get("upstream_sha"), "base_evidence.upstream_sha"
        )
        upstream_tree = _optional_sha(
            data.get("upstream_tree"), "base_evidence.upstream_tree"
        )
        upstream_ref = _optional_string(
            data.get("upstream_ref"), "base_evidence.upstream_ref"
        )
        evidence_source = _require_string(
            data.get("evidence_source"), "base_evidence.evidence_source"
        )
        relation = _require_string(data.get("relation"), "base_evidence.relation")
        if relation not in BASE_RELATIONS:
            raise ClaimError(f"BASE_EVIDENCE_RELATION_INVALID: {relation}")
        if (upstream_sha is None) != (upstream_tree is None):
            raise ClaimError(
                "BASE_EVIDENCE_UPSTREAM_INCOMPLETE: sha/tree must be supplied together"
            )
        expected = _base_relation(local_sha, local_tree, upstream_sha, upstream_tree)
        if relation != expected:
            raise ClaimError(
                f"BASE_EVIDENCE_RELATION_MISMATCH: expected {expected}, received {relation}"
            )
        return cls(
            local_sha=local_sha,
            local_tree=local_tree,
            upstream_sha=upstream_sha,
            upstream_tree=upstream_tree,
            upstream_ref=upstream_ref,
            evidence_source=evidence_source,
            relation=relation,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "local_sha": self.local_sha,
            "local_tree": self.local_tree,
            "upstream_sha": self.upstream_sha,
            "upstream_tree": self.upstream_tree,
            "upstream_ref": self.upstream_ref,
            "evidence_source": self.evidence_source,
            "relation": self.relation,
        }


@dataclass(frozen=True, slots=True)
class ChangeClaim:
    schema_version: int
    change_id: str
    status: str
    branch: str
    worktree: str
    base: str
    outcome: str
    owned_paths: tuple[PathClaim, ...]
    shared_paths: tuple[PathClaim, ...]
    excluded_paths: tuple[PathClaim, ...]
    dependencies: tuple[str, ...]
    integration_owner: str | None
    risk_profile: str | None
    complexity: str | None
    risk_triggers: tuple[str, ...]
    base_evidence: BaseEvidence | None
    work_management: WorkManagementClaim | None
    source: Path
    compatibility_warnings: tuple[str, ...] = ()

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, Any],
        *,
        source: Path,
        historical_compatibility: bool = False,
    ) -> "ChangeClaim":
        missing = sorted(REQUIRED_FIELDS.difference(data))
        if missing:
            raise ClaimError(f"CHANGE_FIELDS_MISSING: {', '.join(missing)}")
        schema_version = data["schema_version"]
        if schema_version not in {1, 2, 3, 4}:
            raise ClaimError("CHANGE_SCHEMA_VERSION_INVALID: expected 1, 2, 3, or 4")
        required_fields = set(REQUIRED_FIELDS)
        allowed_fields = set(REQUIRED_FIELDS)
        if schema_version == 2:
            required_fields.add("work_management")
            allowed_fields.add("work_management")
        elif schema_version == 3:
            required_fields.update({"risk_profile", "base_evidence"})
            allowed_fields.update({"risk_profile", "base_evidence", "work_management"})
        elif schema_version == 4:
            required_fields.update({"complexity", "risk_triggers", "base_evidence"})
            allowed_fields.update(
                {"complexity", "risk_triggers", "base_evidence", "work_management"}
            )
        missing = sorted(required_fields.difference(data))
        unknown = sorted(set(data).difference(allowed_fields))
        if missing:
            raise ClaimError(f"CHANGE_FIELDS_MISSING: {', '.join(missing)}")
        if unknown:
            raise ClaimError(f"CHANGE_FIELDS_UNKNOWN: {', '.join(unknown)}")
        work_management = None
        if "work_management" in data:
            work_data = dict(_require_mapping(data["work_management"], "work_management"))
            if (
                historical_compatibility
                and schema_version == 4
                and "record_id" not in work_data
            ):
                source_number = work_data.get("source_number")
                if (
                    isinstance(source_number, int)
                    and not isinstance(source_number, bool)
                    and source_number > 0
                ):
                    work_data["record_id"] = f"WORK-{source_number}"
            work_management = WorkManagementClaim.from_mapping(work_data)
        risk_profile = None
        complexity = None
        risk_triggers: tuple[str, ...] = ()
        if schema_version < 3:
            risk_profile = "standard"
        elif schema_version == 3:
            risk_profile = _require_string(data["risk_profile"], "risk_profile")
            if risk_profile not in LEGACY_RISK_PROFILES:
                raise ClaimError(f"CHANGE_RISK_PROFILE_INVALID: {risk_profile}")
        else:
            complexity = _require_string(data["complexity"], "complexity")
            if complexity not in COMPLEXITIES:
                raise ClaimError(f"CHANGE_COMPLEXITY_INVALID: {complexity}")
            if historical_compatibility:
                try:
                    risk_triggers = _require_risk_triggers(data["risk_triggers"])
                except ClaimError:
                    risk_triggers = _require_historical_risk_triggers(
                        data["risk_triggers"]
                    )
            else:
                risk_triggers = _require_risk_triggers(data["risk_triggers"])
        base_evidence = None
        if schema_version >= 3:
            raw_base_evidence = _require_mapping(
                data["base_evidence"], "base_evidence"
            )
            if not (
                historical_compatibility
                and schema_version == 4
                and not raw_base_evidence
            ):
                base_evidence = BaseEvidence.from_mapping(raw_base_evidence)

        change_id = _require_change_id(data["change_id"], "change_id")
        status = _require_string(data["status"], "status")
        if status not in ALL_STATUSES:
            raise ClaimError(f"CHANGE_STATUS_INVALID: {status}")

        branch = _require_string(data["branch"], "branch")
        expected_branch = f"change/{change_id}"
        if branch != expected_branch:
            raise ClaimError(
                f"CHANGE_BRANCH_NONSTANDARD: expected {expected_branch}, received {branch}"
            )

        worktree = _require_string(data["worktree"], "worktree")
        expected_worktree = f".work/worktrees/{change_id}"
        if worktree != expected_worktree:
            raise ClaimError(
                "CHANGE_WORKTREE_NONSTANDARD: "
                f"expected {expected_worktree}, received {worktree}"
            )

        base = _require_string(data["base"], "base")
        if (
            base.startswith("-")
            or ".." in base
            or any(character.isspace() for character in base)
        ):
            raise ClaimError(f"CHANGE_BASE_INVALID: {base}")

        outcome = _require_string(data["outcome"], "outcome")
        owned_paths = _require_path_claims(data["owned_paths"], "owned_paths")
        shared_paths = _require_path_claims(data["shared_paths"], "shared_paths")
        excluded_paths = _require_path_claims(data["excluded_paths"], "excluded_paths")
        if not owned_paths:
            raise ClaimError("CHANGE_OWNED_PATHS_EMPTY: at least one path is required")

        dependencies = _require_change_ids(data["dependencies"], "dependencies")
        if change_id in dependencies:
            raise ClaimError("CHANGE_DEPENDENCY_SELF: a change cannot depend on itself")

        owner_value = data["integration_owner"]
        if owner_value is None:
            integration_owner = None
        else:
            try:
                integration_owner = _require_change_id(
                    owner_value, "integration_owner"
                )
            except ClaimError:
                if historical_compatibility and schema_version == 4:
                    _require_string(owner_value, "integration_owner")
                    integration_owner = None
                else:
                    raise

        for owned in owned_paths:
            if any(owned.overlaps(shared) for shared in shared_paths):
                raise ClaimError(
                    f"CHANGE_PATH_CLAIM_CONTRADICTION: {owned.raw} is both owned and shared"
                )
            if any(owned.overlaps(excluded) for excluded in excluded_paths):
                raise ClaimError(
                    f"CHANGE_PATH_CLAIM_CONTRADICTION: {owned.raw} is owned and excluded"
                )
        for shared in shared_paths:
            if any(shared.overlaps(excluded) for excluded in excluded_paths):
                raise ClaimError(
                    f"CHANGE_PATH_CLAIM_CONTRADICTION: {shared.raw} is shared and excluded"
                )

        return cls(
            schema_version=schema_version,
            change_id=change_id,
            status=status,
            branch=branch,
            worktree=worktree,
            base=base,
            outcome=outcome,
            owned_paths=owned_paths,
            shared_paths=shared_paths,
            excluded_paths=excluded_paths,
            dependencies=dependencies,
            integration_owner=integration_owner,
            risk_profile=risk_profile,
            complexity=complexity,
            risk_triggers=risk_triggers,
            base_evidence=base_evidence,
            work_management=work_management,
            source=source,
        )

    @property
    def normalized_outcome(self) -> str:
        return " ".join(self.outcome.casefold().split())

    def to_mapping(self) -> dict[str, Any]:
        mapping = {
            "schema_version": self.schema_version,
            "change_id": self.change_id,
            "status": self.status,
            "branch": self.branch,
            "worktree": self.worktree,
            "base": self.base,
            "outcome": self.outcome,
            "owned_paths": [claim.raw for claim in self.owned_paths],
            "shared_paths": [claim.raw for claim in self.shared_paths],
            "excluded_paths": [claim.raw for claim in self.excluded_paths],
            "dependencies": list(self.dependencies),
            "integration_owner": self.integration_owner,
        }
        if self.schema_version == 3:
            mapping["risk_profile"] = self.risk_profile
            mapping["base_evidence"] = (
                self.base_evidence.to_mapping() if self.base_evidence else None
            )
        elif self.schema_version >= 4:
            mapping["complexity"] = self.complexity
            mapping["risk_triggers"] = list(self.risk_triggers)
            mapping["base_evidence"] = (
                self.base_evidence.to_mapping() if self.base_evidence else None
            )
        if self.work_management is not None:
            mapping["work_management"] = self.work_management.to_mapping()
        return mapping


@dataclass(frozen=True, slots=True)
class WorktreeEntry:
    path: Path
    branch: str | None
    head: str


@dataclass(frozen=True, slots=True)
class CleanupResult:
    change_id: str
    branch: str
    recovered: bool
    backup_path: Path | None

    def to_mapping(self) -> dict[str, Any]:
        return {
            "cleaned": self.change_id,
            "branch": self.branch,
            "recovered": self.recovered,
            "backup_path": str(self.backup_path)
            if self.backup_path is not None
            else None,
        }


def project_pull_request_claims(
    claims: Sequence[ChangeClaim],
    *,
    current_branch: str | None,
) -> list[ChangeClaim]:
    """Release landed schema-v3+ claims while preserving the current PR claim.

    Schema v3 established merge/cleanup as the repository-ownership release point
    without requiring a metadata-only status commit.  In a pull-request checkout,
    merged historical scope files therefore still contain ``active``/``ready`` even
    though their branches are no longer the change being verified.  The current
    GitHub head branch remains active; schema v1/v2 records retain their explicit
    historical status semantics.
    """
    branch = (current_branch or "").strip()
    prefix = "refs/heads/"
    if branch.startswith(prefix):
        branch = branch[len(prefix) :]
    if not branch:
        return list(claims)

    return [
        replace(claim, status="closed")
        if (
            claim.schema_version >= 3
            and claim.status in ACTIVE_STATUSES
            and claim.branch != branch
        )
        else claim
        for claim in claims
    ]


def find_claim_conflicts(claims: Sequence[ChangeClaim]) -> list[str]:
    active = [claim for claim in claims if claim.status in ACTIVE_STATUSES]
    conflicts: list[str] = []

    for index, left in enumerate(active):
        for right in active[index + 1 :]:
            if left.change_id == right.change_id:
                conflicts.append(
                    f"DUPLICATE_CHANGE_ID: {left.change_id} in {left.source} and {right.source}"
                )
            if left.branch == right.branch:
                conflicts.append(
                    f"DUPLICATE_ACTIVE_BRANCH: {left.branch} in {left.source} and {right.source}"
                )
            if left.worktree == right.worktree:
                conflicts.append(
                    "DUPLICATE_ACTIVE_WORKTREE: "
                    f"{left.worktree} in {left.source} and {right.source}"
                )
            if left.normalized_outcome == right.normalized_outcome:
                conflicts.append(
                    "DUPLICATE_ACTIVE_OUTCOME: "
                    f"{left.outcome!r} in {left.source} and {right.source}"
                )
            conflicts.extend(_path_conflicts(left, right))

    return conflicts


def paths_outside_claim(claim: ChangeClaim, paths: Iterable[str]) -> list[str]:
    violations: list[str] = []
    seen: set[str] = set()
    declared = (*claim.owned_paths, *claim.shared_paths)
    for raw_path in paths:
        normalized = _normalize_repository_path(raw_path)
        if normalized in seen:
            continue
        seen.add(normalized)
        if any(path_claim.matches(normalized) for path_claim in claim.excluded_paths):
            violations.append(f"PATH_EXCLUDED_BY_CLAIM: {normalized}")
        elif not any(path_claim.matches(normalized) for path_claim in declared):
            violations.append(f"PATH_OUTSIDE_CLAIM: {normalized}")
    return violations


def _project_historical_schema_v4(
    data: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    projected = dict(data)
    warnings: list[str] = []
    if projected.get("schema_version") != 4:
        return projected, ()
    change_id = projected.get("change_id")
    if (
        "owned_paths" not in projected
        and isinstance(change_id, str)
        and CHANGE_ID_PATTERN.fullmatch(change_id)
    ):
        projected["owned_paths"] = [f".work/changes/{change_id}/**"]
        warnings.append("HISTORICAL_OWNED_PATHS_DEFAULTED_TO_CHANGE_RECORD")
    for field in ("shared_paths", "excluded_paths", "dependencies"):
        if field not in projected:
            projected[field] = []
            warnings.append(f"HISTORICAL_{field.upper()}_DEFAULTED_EMPTY")
    projected.setdefault("integration_owner", None)
    projected.setdefault("risk_triggers", [])
    if projected.get("base_evidence") is None:
        projected["base_evidence"] = {}
        warnings.append("HISTORICAL_BASE_EVIDENCE_UNAVAILABLE")
    dependencies = projected.get("dependencies")
    if isinstance(dependencies, list):
        retained: list[str] = []
        for item in dependencies:
            if isinstance(item, str) and CHANGE_ID_PATTERN.fullmatch(item):
                retained.append(item)
            else:
                warnings.append(f"HISTORICAL_DEPENDENCY_UNRESOLVED:{item}")
        projected["dependencies"] = retained
    owner = projected.get("integration_owner")
    if owner is not None and (
        not isinstance(owner, str) or CHANGE_ID_PATTERN.fullmatch(owner) is None
    ):
        warnings.append(f"HISTORICAL_INTEGRATION_OWNER_UNRESOLVED:{owner}")
    risk_triggers = projected.get("risk_triggers")
    if isinstance(risk_triggers, list):
        unknown = [item for item in risk_triggers if item not in RISK_TRIGGERS]
        if unknown:
            warnings.append("HISTORICAL_RISK_TRIGGERS_PRESERVED:" + ",".join(unknown))
    work_management = projected.get("work_management")
    if isinstance(work_management, Mapping):
        work_data = dict(work_management)
        if "record_id" not in work_data:
            warnings.append("HISTORICAL_WORK_RECORD_ID_SYNTHESIZED")
        if "documentation_impact" not in work_data:
            work_data["documentation_impact"] = "not_assessed"
            warnings.append("HISTORICAL_DOCUMENTATION_IMPACT_DEFAULTED")
        projected["work_management"] = work_data
    return projected, tuple(warnings)


def load_claim(
    path: Path,
    *,
    historical_compatibility: bool = False,
) -> ChangeClaim:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ClaimError(f"CHANGE_SCOPE_UNREADABLE: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ClaimError(f"CHANGE_SCOPE_INVALID: {path} must contain a JSON object")
    warnings: tuple[str, ...] = ()
    if historical_compatibility:
        data, warnings = _project_historical_schema_v4(data)
    claim = ChangeClaim.from_mapping(
        data,
        source=path,
        historical_compatibility=historical_compatibility,
    )
    return replace(claim, compatibility_warnings=warnings) if warnings else claim


def _scope_record_exists_on_base(root: Path, base: str, change_id: str) -> bool:
    probe = _run_git(
        root,
        "cat-file",
        "-e",
        f"{base}:.work/changes/{change_id}/scope.json",
        check=False,
    )
    return probe.returncode == 0


def _scope_is_historical_by_topology(root: Path, path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict) or data.get("schema_version") != 4:
        return False
    change_id = data.get("change_id")
    branch = data.get("branch")
    base = data.get("base")
    if (
        not isinstance(change_id, str)
        or CHANGE_ID_PATTERN.fullmatch(change_id) is None
        or not isinstance(branch, str)
        or not branch
        or not isinstance(base, str)
        or not base
    ):
        return False
    if not _scope_record_exists_on_base(root, base, change_id):
        return False
    if not _git_ref_exists(root, f"refs/heads/{branch}"):
        return True
    landed = _run_git(
        root,
        "merge-base",
        "--is-ancestor",
        branch,
        base,
        check=False,
    )
    return landed.returncode == 0


def _load_claim_for_inventory(root: Path, path: Path) -> ChangeClaim:
    try:
        return load_claim(path)
    except ClaimError:
        if not _scope_is_historical_by_topology(root, path):
            raise
        return load_claim(path, historical_compatibility=True)


def _claim_is_released(root: Path, claim: ChangeClaim) -> bool:
    if claim.schema_version < 3:
        return False
    if not _scope_record_exists_on_base(root, claim.base, claim.change_id):
        return False
    if not _git_ref_exists(root, f"refs/heads/{claim.branch}"):
        return True
    landed = _run_git(
        root,
        "merge-base",
        "--is-ancestor",
        claim.branch,
        claim.base,
        check=False,
    )
    return landed.returncode == 0


def discover_worktrees(repository: Path) -> list[WorktreeEntry]:
    root = repository_root(repository)
    output = _run_git(root, "worktree", "list", "--porcelain").stdout
    entries: list[WorktreeEntry] = []
    current: dict[str, str] = {}
    for line in [*output.splitlines(), ""]:
        if not line:
            if current:
                entries.append(
                    WorktreeEntry(
                        path=Path(current["worktree"]).resolve(),
                        branch=_normalize_branch_ref(current.get("branch")),
                        head=current.get("HEAD", ""),
                    )
                )
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    return entries


def load_worktree_claims(repository: Path) -> list[ChangeClaim]:
    worktrees = discover_worktrees(repository)
    if not worktrees:
        return []

    current_root = repository_root(repository)
    claims = _claims_in_checkout(current_root, allow_historical=True)
    known_change_ids = {claim.change_id for claim in claims}

    for entry in worktrees:
        if not entry.branch or not entry.branch.startswith("change/"):
            continue
        change_id = entry.branch.removeprefix("change/")
        if change_id in known_change_ids:
            continue
        scope_path = entry.path / ".work" / "changes" / change_id / "scope.json"
        if not scope_path.is_file():
            continue
        claims.append(_load_claim_for_inventory(current_root, scope_path))
        known_change_ids.add(change_id)

    return [
        replace(claim, status="closed")
        if claim.status in ACTIVE_STATUSES and _claim_is_released(current_root, claim)
        else claim
        for claim in claims
    ]


def _write_text_lf(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def _capture_base_evidence(
    root: Path,
    base: str,
    *,
    upstream_sha: str | None = None,
    upstream_tree: str | None = None,
    upstream_ref: str | None = None,
) -> BaseEvidence:
    local_sha = _require_sha(
        _run_git(root, "rev-parse", "--verify", f"{base}^{{commit}}").stdout.strip(),
        "base_evidence.local_sha",
    )
    local_tree = _require_sha(
        _run_git(root, "rev-parse", "--verify", f"{local_sha}^{{tree}}").stdout.strip(),
        "base_evidence.local_tree",
    )
    supplied_sha = _optional_sha(upstream_sha, "upstream_sha")
    supplied_tree = _optional_sha(upstream_tree, "upstream_tree")
    if (supplied_sha is None) != (supplied_tree is None):
        raise ClaimError(
            "BASE_EVIDENCE_UPSTREAM_INCOMPLETE: sha/tree must be supplied together"
        )
    ref = _optional_string(upstream_ref, "upstream_ref")
    evidence_source = "provided" if supplied_sha is not None else "unavailable"
    if supplied_sha is None:
        candidate = ref or f"refs/remotes/origin/{base}"
        if _git_ref_exists(root, candidate):
            supplied_sha = _require_sha(
                _run_git(
                    root, "rev-parse", "--verify", f"{candidate}^{{commit}}"
                ).stdout.strip(),
                "base_evidence.upstream_sha",
            )
            supplied_tree = _require_sha(
                _run_git(
                    root, "rev-parse", "--verify", f"{supplied_sha}^{{tree}}"
                ).stdout.strip(),
                "base_evidence.upstream_tree",
            )
            ref = candidate
            evidence_source = "local_remote_tracking_ref"
        else:
            ref = None
    return BaseEvidence(
        local_sha=local_sha,
        local_tree=local_tree,
        upstream_sha=supplied_sha,
        upstream_tree=supplied_tree,
        upstream_ref=ref,
        evidence_source=evidence_source,
        relation=_base_relation(local_sha, local_tree, supplied_sha, supplied_tree),
    )


def _state_root() -> Path:
    return Path(os.environ.get("KIS_STATE_ROOT", str(DEFAULT_STATE_ROOT))).resolve()


@contextmanager
def _change_admission_lock(root: Path) -> Iterator[None]:
    repository_key = hashlib.sha256(
        str(root.resolve()).casefold().encode("utf-8")
    ).hexdigest()[:24]
    lock_path = _state_root() / "change-governance" / f"{repository_key}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as stream:
        stream.seek(0)
        _lock_file(stream)
        try:
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
                os.fsync(stream.fileno())
            stream.seek(0)
            yield
        finally:
            _unlock_file(stream)


def _lock_file(stream: Any) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        return
    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_EX)


def _unlock_file(stream: Any) -> None:
    if os.name == "nt":
        import msvcrt

        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _serialized_change_creation(function: Any) -> Any:
    @wraps(function)
    def wrapped(repository: Path, *args: Any, **kwargs: Any) -> Path:
        root = repository_root(repository)
        with _change_admission_lock(root):
            return function(root, *args, **kwargs)

    return wrapped


def _change_number(change_id: str) -> str:
    return change_id.split("-", 1)[0]


def _governed_ref_change_ids(root: Path) -> tuple[tuple[str, str], ...]:
    output = _run_git(
        root,
        "for-each-ref",
        "--format=%(refname)",
        "refs/heads",
        "refs/remotes",
    ).stdout
    found: list[tuple[str, str]] = []
    for ref in output.splitlines():
        match = re.search(r"/change/(?P<change_id>[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*)$", ref)
        if match is not None:
            found.append((match.group("change_id"), ref))
    return tuple(found)


def _change_number_inventory(
    root: Path,
    claims: Sequence[ChangeClaim],
) -> tuple[tuple[str, str], ...]:
    identities: set[tuple[str, str]] = set()
    for claim in claims:
        identities.add((claim.change_id, f"scope:{claim.source}"))
    for existing_id, ref in _governed_ref_change_ids(root):
        identities.add((existing_id, f"ref:{ref}"))
    for entry in discover_worktrees(root):
        candidate = entry.path.name
        if CHANGE_ID_PATTERN.fullmatch(candidate):
            identities.add((candidate, f"worktree:{entry.path}"))
    return tuple(sorted(identities))


def _require_unique_change_number(
    root: Path,
    change_id: str,
    claims: Sequence[ChangeClaim],
) -> None:
    number = _change_number(change_id)
    conflicts = [
        f"{source}:{existing_id}"
        for existing_id, source in _change_number_inventory(root, claims)
        if _change_number(existing_id) == number
    ]
    if conflicts:
        detail = "; ".join(conflicts)
        raise ClaimError(
            f"DUPLICATE_CHANGE_NUMBER: {number} requested by {change_id}; conflicts with {detail}"
        )


def _require_explicit_change_id(
    root: Path,
    change_id: str,
    claims: Sequence[ChangeClaim],
) -> str:
    normalized = _require_change_id(change_id, "change_id")
    _require_unique_change_number(root, normalized, claims)
    return normalized


def _allocate_change_id(
    root: Path,
    slug: str,
    claims: Sequence[ChangeClaim],
) -> str:
    normalized_slug = _require_string(slug, "change_slug")
    if CHANGE_SLUG_PATTERN.fullmatch(normalized_slug) is None:
        raise ClaimError(f"CHANGE_SLUG_INVALID: {normalized_slug}")
    numbers = [
        int(_change_number(existing_id))
        for existing_id, _source in _change_number_inventory(root, claims)
    ]
    next_number = max(numbers, default=0) + 1
    if next_number > 999:
        raise ClaimError("CHANGE_NUMBER_EXHAUSTED: no three-digit change number remains")
    return f"{next_number:03d}-{normalized_slug}"


@_serialized_change_creation
def create_change_worktree(
    repository: Path,
    *,
    change_id: str,
    outcome: str,
    owned_paths: Sequence[str],
    shared_paths: Sequence[str] = (),
    excluded_paths: Sequence[str] = (),
    dependencies: Sequence[str] = (),
    integration_owner: str | None = None,
    work_management: Mapping[str, Any] | WorkManagementClaim | None = None,
    complexity: str = "medium",
    risk_triggers: Sequence[str] = (),
    upstream_sha: str | None = None,
    upstream_tree: str | None = None,
    upstream_ref: str | None = None,
    base: str = "main",
    allocate_next: bool = False,
) -> Path:
    root = repository_root(repository)
    normalized_complexity = _require_string(complexity, "complexity")
    if normalized_complexity not in COMPLEXITIES:
        raise ClaimError(f"CHANGE_COMPLEXITY_INVALID: {normalized_complexity}")
    normalized_triggers = _require_risk_triggers(sorted(set(risk_triggers)))
    work_management_claim = None
    if work_management is not None:
        work_management_claim = (
            work_management
            if isinstance(work_management, WorkManagementClaim)
            else WorkManagementClaim.from_mapping(
                _require_mapping(work_management, "work_management")
            )
        )
    _require_primary_clean_worktree(root, base)
    _require_worktree_directory_ignored(root)
    _require_template(root)
    existing_claims = validate_repository(root)
    change_id = (
        _allocate_change_id(root, change_id, existing_claims)
        if allocate_next
        else _require_explicit_change_id(root, change_id, existing_claims)
    )
    base_evidence = _capture_base_evidence(
        root,
        base,
        upstream_sha=upstream_sha,
        upstream_tree=upstream_tree,
        upstream_ref=upstream_ref,
    )

    workspace_claim = f".work/changes/{change_id}/**"
    normalized_owned = list(owned_paths)
    if workspace_claim not in normalized_owned:
        normalized_owned.append(workspace_claim)
    claim_data = {
        "schema_version": 4,
        "change_id": change_id,
        "status": "active",
        "branch": f"change/{change_id}",
        "worktree": f".work/worktrees/{change_id}",
        "base": base,
        "outcome": outcome,
        "owned_paths": normalized_owned,
        "shared_paths": list(shared_paths),
        "excluded_paths": list(excluded_paths),
        "dependencies": list(dependencies),
        "integration_owner": integration_owner,
        "complexity": normalized_complexity,
        "risk_triggers": list(normalized_triggers),
        "base_evidence": base_evidence.to_mapping(),
    }
    if work_management_claim is not None:
        claim_data["work_management"] = work_management_claim.to_mapping()
    claim = ChangeClaim.from_mapping(claim_data, source=Path("<new-change>"))
    conflicts = find_claim_conflicts([*existing_claims, claim])
    if conflicts:
        raise ClaimError("\n".join(conflicts))

    branch = claim.branch
    target = root / claim.worktree
    if target.exists():
        raise ClaimError(f"CHANGE_WORKTREE_EXISTS: {target}")
    if _git_ref_exists(root, f"refs/heads/{branch}"):
        raise ClaimError(f"CHANGE_BRANCH_EXISTS: {branch}")
    if not _git_ref_exists(root, f"refs/heads/{base}"):
        raise ClaimError(f"CHANGE_BASE_MISSING: {base}")

    target.parent.mkdir(parents=True, exist_ok=True)
    _run_git(root, "worktree", "add", str(target), "-b", branch, base)
    try:
        change_root = target / ".work" / "changes" / change_id
        change_root.mkdir(parents=True, exist_ok=False)
        _write_text_lf(
            change_root / "scope.json",
            json.dumps(claim.to_mapping(), indent=2) + "\n",
        )
        template_root = root / ".work" / "changes" / "_template"
        replacements = {
            "{{CHANGE_ID}}": change_id,
            "{{CHANGE_NAME}}": change_id.split("-", 1)[1].replace("-", " ").title(),
            "{{OUTCOME}}": outcome,
        }
        for name in _required_change_files(claim)[1:]:
            content = (template_root / name).read_text(encoding="utf-8")
            for marker, replacement in replacements.items():
                content = content.replace(marker, replacement)
            _write_text_lf(change_root / name, content)
    except Exception:
        _run_git(root, "worktree", "remove", str(target), check=False)
        _run_git(root, "branch", "-d", branch, check=False)
        raise
    return target


def validate_repository(
    repository: Path,
    *,
    require_active_worktrees: bool = True,
) -> list[ChangeClaim]:
    current_root = repository_root(repository)
    worktrees = discover_worktrees(current_root)
    if not worktrees:
        raise ClaimError("PRIMARY_WORKTREE_UNRESOLVED: no Git worktrees were found")
    primary_root = worktrees[0].path
    _require_worktree_directory_ignored(primary_root)
    template_root = (
        current_root
        if (current_root / ".work" / "changes" / "_template").is_dir()
        else primary_root
    )
    _require_template(template_root)
    claims = load_worktree_claims(current_root)
    conflicts = find_claim_conflicts(claims)
    if conflicts:
        raise ClaimError("\n".join(conflicts))
    entries = {entry.branch: entry for entry in worktrees if entry.branch}
    claims_by_branch: dict[str, list[ChangeClaim]] = {}
    for claim in claims:
        claims_by_branch.setdefault(claim.branch, []).append(claim)

    for entry in worktrees[1:]:
        if not entry.branch or not entry.branch.startswith("change/"):
            continue
        registered = claims_by_branch.get(entry.branch, [])
        if not registered:
            raise ClaimError(f"ACTIVE_CHANGE_CLAIM_MISSING: {entry.branch}")
        expected = (primary_root / registered[0].worktree).resolve()
        if entry.path != expected:
            raise ClaimError(
                f"ACTIVE_CHANGE_WORKTREE_MISMATCH: {registered[0].change_id}: "
                f"{entry.path} != {expected}"
            )

    if require_active_worktrees:
        for claim in claims:
            if claim.status not in ACTIVE_STATUSES:
                continue
            entry = entries.get(claim.branch)
            if entry is None:
                raise ClaimError(f"ACTIVE_CHANGE_WORKTREE_MISSING: {claim.change_id}")
    return claims


def orphaned_change_worktrees(repository: Path) -> list[dict[str, str]]:
    root = repository_root(repository)
    worktrees = discover_worktrees(root)
    claims = load_worktree_claims(root)
    claimed = {claim.branch for claim in claims}
    return [
        {"branch": entry.branch, "path": str(entry.path)}
        for entry in worktrees[1:]
        if entry.branch
        and entry.branch.startswith("change/")
        and entry.branch not in claimed
    ]


def check_current_change(repository: Path) -> list[str]:
    root = repository_root(repository)
    branch = _run_git(root, "branch", "--show-current").stdout.strip()
    if not branch:
        raise ClaimError("CHANGE_BRANCH_DETACHED: current worktree has no branch")
    if not branch.startswith("change/"):
        raise ClaimError(f"CURRENT_CHANGE_CLAIM_MISSING: current branch is {branch}")
    change_id = _require_change_id(
        branch.removeprefix("change/"),
        "current_change_id",
    )
    scope_path = root / ".work" / "changes" / change_id / "scope.json"
    if not scope_path.is_file():
        raise ClaimError(f"CURRENT_CHANGE_CLAIM_MISSING: no scope for {branch}")
    claim = load_claim(scope_path, historical_compatibility=False)
    if claim.branch != branch:
        raise ClaimError(
            f"CURRENT_CHANGE_CLAIM_MISMATCH: {claim.branch} != {branch}"
        )
    _require_change_artifacts(root, claim)
    merge_base = _run_git(root, "merge-base", claim.base, "HEAD").stdout.strip()
    committed = _run_git(
        root, "diff", "--name-only", f"{merge_base}...HEAD"
    ).stdout.splitlines()
    working = _working_tree_paths(root)
    changed = [*committed, *working]
    violations = paths_outside_claim(claim, changed)
    if violations:
        raise ClaimError("\n".join(violations))
    return sorted(set(changed))


def retire_closed_orphan_worktree(
    repository: Path,
    change_id: str,
    *,
    terminal_work_confirmed: bool,
) -> CleanupResult:
    root = repository_root(repository)
    normalized_id = _require_change_id(change_id, "change_id")
    if not terminal_work_confirmed:
        raise ClaimError(f"TERMINAL_WORK_EVIDENCE_REQUIRED: {normalized_id}")
    branch = f"change/{normalized_id}"
    entries = {entry.branch: entry for entry in discover_worktrees(root) if entry.branch}
    entry = entries.get(branch)
    if entry is None:
        raise ClaimError(f"CHANGE_WORKTREE_MISSING: {normalized_id}")
    target = entry.path.resolve()
    worktree_root = (root / ".work" / "worktrees").resolve()
    if worktree_root not in target.parents:
        raise ClaimError(f"ORPHAN_WORKTREE_PATH_UNSAFE: {target}")
    claims = [claim for claim in load_worktree_claims(root) if claim.branch == branch]
    if claims:
        raise ClaimError(f"ORPHAN_CHANGE_CLAIM_PRESENT: {normalized_id}")
    status_result = _run_git(
        target,
        "status",
        "--porcelain",
        "--untracked-files=all",
        check=False,
    )
    status_unknown = status_result.returncode != 0
    status = status_result.stdout
    head = _run_git(target, "rev-parse", "HEAD").stdout.strip()
    recovered = False
    backup_path: Path | None = None
    if status_unknown or status.strip():
        backup_root = root.parent / ".backup"
        backup_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_path = backup_root / f"{normalized_id}-orphan-worktree-{timestamp}"
        if backup_path.exists():
            raise ClaimError(f"CHANGE_BACKUP_EXISTS: {backup_path}")
        try:
            target.replace(backup_path)
        except OSError as exc:
            raise ClaimError(
                f"CHANGE_WORKTREE_RECOVERY_FAILED: {target} -> {backup_path}: {exc}"
            ) from exc
        _run_git(root, "worktree", "prune", "--expire", "now")
        remaining = {
            worktree.branch: worktree
            for worktree in discover_worktrees(root)
            if worktree.branch
        }
        if branch in remaining:
            raise ClaimError(
                f"CHANGE_WORKTREE_REMOVE_FAILED: {branch} remains registered after recoverable move"
            )
        recovered = True
    else:
        removal = _run_git(
            root,
            "-c",
            "core.longpaths=true",
            "worktree",
            "remove",
            str(target),
            check=False,
        )
        if removal.returncode != 0:
            remaining = {
                worktree.branch: worktree
                for worktree in discover_worktrees(root)
                if worktree.branch
            }
            if branch in remaining:
                detail = removal.stderr.strip() or removal.stdout.strip() or "unknown removal failure"
                raise ClaimError(f"CHANGE_WORKTREE_REMOVE_FAILED: {branch} remains registered: {detail}")
            if target.exists():
                backup_root = root.parent / ".backup"
                backup_root.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                backup_path = backup_root / f"{normalized_id}-orphan-worktree-remnant-{timestamp}"
                if backup_path.exists():
                    raise ClaimError(f"CHANGE_BACKUP_EXISTS: {backup_path}")
                target.replace(backup_path)
                recovered = True
    preserved = _run_git(root, "rev-parse", branch).stdout.strip()
    if preserved != head:
        raise ClaimError(f"ORPHAN_BRANCH_PRESERVATION_FAILED: {branch}: {preserved} != {head}")
    _run_git(root, "worktree", "prune")
    return CleanupResult(change_id=normalized_id, branch=branch, recovered=recovered, backup_path=backup_path)


def cleanup_change_worktree(repository: Path, change_id: str) -> CleanupResult:
    root = repository_root(repository)
    normalized_id = _require_change_id(change_id, "change_id")
    target = (root / ".work" / "worktrees" / normalized_id).resolve()
    branch = f"change/{normalized_id}"
    entries = {
        entry.branch: entry for entry in discover_worktrees(root) if entry.branch
    }
    entry = entries.get(branch)
    if entry is None or entry.path != target:
        raise ClaimError(f"CHANGE_WORKTREE_MISSING: {normalized_id}")

    status = _run_git(target, "status", "--porcelain", "--untracked-files=all").stdout
    if status.strip():
        raise ClaimError(f"CHANGE_WORKTREE_DIRTY: {target}")

    claims = [
        claim
        for claim in _claims_in_checkout(target, allow_historical=True)
        if claim.change_id == normalized_id
    ]
    if len(claims) != 1:
        raise ClaimError(f"CHANGE_SCOPE_MISSING: {normalized_id}")
    claim = claims[0]
    if claim.schema_version < 3 and claim.status != "closed":
        raise ClaimError(
            f"CHANGE_STATUS_NOT_CLOSED: {normalized_id}: status is {claim.status}"
        )
    base = claim.base
    ancestor = _run_git(root, "merge-base", "--is-ancestor", branch, base, check=False)
    if ancestor.returncode != 0:
        raise ClaimError(f"CHANGE_BRANCH_UNMERGED: {branch} is not merged into {base}")

    removal = _run_git(
        root,
        "-c",
        "core.longpaths=true",
        "worktree",
        "remove",
        str(target),
        check=False,
    )
    recovered = False
    backup_path: Path | None = None
    if removal.returncode != 0:
        remaining = {
            worktree.branch: worktree
            for worktree in discover_worktrees(root)
            if worktree.branch
        }
        if branch in remaining:
            detail = (
                removal.stderr.strip()
                or removal.stdout.strip()
                or "unknown removal failure"
            )
            raise ClaimError(
                f"CHANGE_WORKTREE_REMOVE_FAILED: {branch} remains registered: {detail}"
            )
        if target.exists():
            backup_root = root.parent / ".backup"
            backup_root.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            backup_path = backup_root / f"{normalized_id}-worktree-remnant-{timestamp}"
            if backup_path.exists():
                raise ClaimError(f"CHANGE_BACKUP_EXISTS: {backup_path}")
            try:
                target.replace(backup_path)
            except OSError as exc:
                raise ClaimError(
                    f"CHANGE_WORKTREE_RECOVERY_FAILED: {target} -> {backup_path}: {exc}"
                ) from exc
            recovered = True

    _run_git(root, "branch", "-d", branch)
    _run_git(root, "worktree", "prune")
    return CleanupResult(
        change_id=normalized_id,
        branch=branch,
        recovered=recovered,
        backup_path=backup_path,
    )


def repository_root(path: Path) -> Path:
    candidate = Path(path).resolve()
    result = _run_git(candidate, "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip()).resolve()


def _path_intersection(left: PathClaim, right: PathClaim) -> str | None:
    if not left.overlaps(right):
        return None
    if not left.recursive and not right.recursive:
        return left.raw
    if left.recursive and right.recursive:
        deeper = left if _is_same_or_descendant(left.prefix, right.prefix) else right
        return f"{deeper.prefix}/**"
    recursive = left if left.recursive else right
    exact = right if left.recursive else left
    if _is_same_or_descendant(exact.prefix, recursive.prefix):
        return exact.raw
    return None


def _path_conflicts(left: ChangeClaim, right: ChangeClaim) -> list[str]:
    conflicts: list[str] = []
    for left_owned in left.owned_paths:
        for right_claim in (*right.owned_paths, *right.shared_paths):
            intersection = _path_intersection(left_owned, right_claim)
            if intersection is not None:
                conflicts.append(
                    "EXCLUSIVE_PATH_OVERLAP: "
                    f"{left.change_id}:{left_owned.raw} overlaps "
                    f"{right.change_id}:{right_claim.raw}; intersection={intersection}"
                )
    for right_owned in right.owned_paths:
        for left_shared in left.shared_paths:
            intersection = _path_intersection(right_owned, left_shared)
            if intersection is not None:
                conflicts.append(
                    "EXCLUSIVE_PATH_OVERLAP: "
                    f"{right.change_id}:{right_owned.raw} overlaps "
                    f"{left.change_id}:{left_shared.raw}; intersection={intersection}"
                )
    for left_shared in left.shared_paths:
        for right_shared in right.shared_paths:
            intersection = _path_intersection(left_shared, right_shared)
            if intersection is not None and not _claims_are_coordinated(left, right):
                conflicts.append(
                    "UNCOORDINATED_SHARED_PATH: "
                    f"{left.change_id}:{left_shared.raw} overlaps "
                    f"{right.change_id}:{right_shared.raw}; intersection={intersection}"
                )
    return conflicts


def _claims_are_coordinated(left: ChangeClaim, right: ChangeClaim) -> bool:
    if left.change_id in right.dependencies or right.change_id in left.dependencies:
        return True
    if left.integration_owner and left.integration_owner == right.integration_owner:
        return True
    if (
        left.integration_owner == right.change_id
        or right.integration_owner == left.change_id
    ):
        return True
    return False


def _claims_in_checkout(
    root: Path,
    *,
    allow_historical: bool = False,
) -> list[ChangeClaim]:
    changes_root = root / ".work" / "changes"
    if not changes_root.is_dir():
        return []
    claims: list[ChangeClaim] = []
    repository = repository_root(root)
    for scope_path in sorted(changes_root.glob("*/scope.json")):
        if scope_path.parent.name.startswith("_"):
            continue
        claim = (
            _load_claim_for_inventory(repository, scope_path)
            if allow_historical
            else load_claim(scope_path)
        )
        claims.append(claim)
    return claims


def _require_primary_clean_worktree(root: Path, base: str) -> None:
    entries = discover_worktrees(root)
    if not entries or entries[0].path != root:
        raise ClaimError(
            "PRIMARY_WORKTREE_UNRESOLVED: cannot determine the primary checkout"
        )
    current = _run_git(root, "branch", "--show-current").stdout.strip()
    if current != base:
        raise ClaimError(
            f"PRIMARY_BRANCH_REQUIRED: expected {base}, received {current or '<detached>'}"
        )
    status = _run_git(root, "status", "--porcelain", "--untracked-files=all").stdout
    if status.strip():
        raise ClaimError(
            "PRIMARY_WORKTREE_DIRTY: commit or quarantine current changes first"
        )


def _require_worktree_directory_ignored(root: Path) -> None:
    probe = ".work/worktrees/.governance-probe"
    result = _run_git(root, "check-ignore", "-q", probe, check=False)
    if result.returncode != 0:
        raise ClaimError(
            "WORKTREE_DIRECTORY_NOT_IGNORED: add .work/worktrees/ to .gitignore"
        )


def _required_change_files(claim: ChangeClaim) -> tuple[str, ...]:
    if claim.schema_version == 3:
        return (
            LEGACY_COMPACT_CHANGE_FILES
            if claim.risk_profile == "lean"
            else LEGACY_FULL_CHANGE_FILES
        )
    if claim.schema_version >= 4:
        if claim.complexity not in CHANGE_FILES_BY_COMPLEXITY:
            raise ClaimError(f"CHANGE_COMPLEXITY_INVALID: {claim.complexity}")
        return CHANGE_FILES_BY_COMPLEXITY[claim.complexity]
    return LEGACY_FULL_CHANGE_FILES


def _require_template(root: Path) -> None:
    template = root / ".work" / "changes" / "_template"
    missing = [
        name for name in TEMPLATE_CHANGE_FILES if not (template / name).is_file()
    ]
    if missing:
        raise ClaimError(f"CHANGE_TEMPLATE_MISSING: {', '.join(missing)}")


def _require_change_artifacts(root: Path, claim: ChangeClaim) -> None:
    change_root = root / ".work" / "changes" / claim.change_id
    missing = [
        name
        for name in _required_change_files(claim)
        if not (change_root / name).is_file()
    ]
    if missing:
        raise ClaimError(
            f"CHANGE_ARTIFACTS_MISSING: {claim.change_id}: {', '.join(missing)}"
        )


def _working_tree_paths(root: Path) -> list[str]:
    output = _run_git(root, "status", "--porcelain", "--untracked-files=all").stdout
    paths: list[str] = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        value = line[3:]
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        paths.append(value.strip('"'))
    return paths


def _git_ref_exists(root: Path, ref: str) -> bool:
    return (
        _run_git(root, "show-ref", "--verify", "--quiet", ref, check=False).returncode
        == 0
    )


def _run_git(
    repository: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and completed.returncode != 0:
        detail = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or "unknown git failure"
        )
        raise ClaimError(f"GIT_COMMAND_FAILED: git {' '.join(args)}: {detail}")
    return completed


def _normalize_branch_ref(value: str | None) -> str | None:
    prefix = "refs/heads/"
    if value and value.startswith(prefix):
        return value[len(prefix) :]
    return value


def _require_path_claims(value: Any, field: str) -> tuple[PathClaim, ...]:
    raw_values = _require_string_list(value, field)
    claims = tuple(_parse_path_claim(raw) for raw in raw_values)
    if len({claim.raw for claim in claims}) != len(claims):
        raise ClaimError(f"CHANGE_PATH_DUPLICATE: {field}")
    return claims


def _require_change_ids(value: Any, field: str) -> tuple[str, ...]:
    values = _require_string_list(value, field)
    normalized = tuple(_require_change_id(item, field) for item in values)
    if len(set(normalized)) != len(normalized):
        raise ClaimError(f"CHANGE_ID_DUPLICATE: {field}")
    return normalized


def _require_risk_triggers(value: Any) -> tuple[str, ...]:
    values = _require_string_list(value, "risk_triggers")
    if len(set(values)) != len(values):
        raise ClaimError("CHANGE_RISK_TRIGGER_DUPLICATE: risk_triggers")
    unknown = sorted(set(values).difference(RISK_TRIGGERS))
    if unknown:
        raise ClaimError(f"CHANGE_RISK_TRIGGER_INVALID: {', '.join(unknown)}")
    if tuple(values) != tuple(sorted(values)):
        raise ClaimError(
            "CHANGE_RISK_TRIGGER_ORDER_INVALID: risk_triggers must be sorted"
        )
    return tuple(values)


def _require_historical_risk_triggers(value: Any) -> tuple[str, ...]:
    values = _require_string_list(value, "risk_triggers")
    normalized = tuple(_require_string(item, "risk_triggers") for item in values)
    if len(set(normalized)) != len(normalized):
        raise ClaimError("CHANGE_RISK_TRIGGER_DUPLICATE: risk_triggers")
    return normalized


def _require_string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ClaimError(f"CHANGE_FIELD_TYPE_INVALID: {field} must be a string array")
    return tuple(value)


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ClaimError(f"CHANGE_FIELD_TYPE_INVALID: {field} must be an object")
    return value


def _require_change_id(value: Any, field: str) -> str:
    text = _require_string(value, field)
    if not CHANGE_ID_PATTERN.fullmatch(text):
        raise ClaimError(f"CHANGE_ID_INVALID: {field}={text}")
    return text


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClaimError(
            f"CHANGE_FIELD_TYPE_INVALID: {field} must be a non-empty string"
        )
    return value.strip()


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, field)


def _require_sha(value: Any, field: str) -> str:
    text = _require_string(value, field).lower()
    if re.fullmatch(r"[0-9a-f]{40}", text) is None:
        raise ClaimError(f"CHANGE_SHA_INVALID: {field}")
    return text


def _optional_sha(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _require_sha(value, field)


def _base_relation(
    local_sha: str, local_tree: str, upstream_sha: str | None, upstream_tree: str | None
) -> str:
    if upstream_sha is None or upstream_tree is None:
        return "unavailable"
    if local_sha == upstream_sha:
        return "same_sha"
    if local_tree == upstream_tree:
        return "tree_equivalent"
    return "content_divergence"


def _parse_path_claim(value: str) -> PathClaim:
    normalized = _normalize_repository_path(value)
    recursive = normalized.endswith("/**")
    if "*" in normalized and not recursive:
        raise ClaimError(f"CHANGE_PATH_PATTERN_INVALID: {value}")
    prefix = normalized[:-3] if recursive else normalized
    if not prefix or "*" in prefix:
        raise ClaimError(f"CHANGE_PATH_PATTERN_INVALID: {value}")
    return PathClaim(raw=normalized, prefix=prefix, recursive=recursive)


def _normalize_repository_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClaimError("CHANGE_PATH_PATTERN_INVALID: path must be non-empty")
    normalized = value.strip().replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
        raise ClaimError(f"CHANGE_PATH_PATTERN_INVALID: {value}")
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ClaimError(f"CHANGE_PATH_PATTERN_INVALID: {value}")
    return normalized


def _is_same_or_descendant(path: str, parent: str) -> bool:
    return path == parent or path.startswith(f"{parent}/")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage bounded parallel change worktrees."
    )
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)

    new = subparsers.add_parser("new", help="Create one validated change worktree.")
    new.add_argument(
        "change_id",
        help="Canonical NNN-slug change ID, or slug only when --allocate-next is used.",
    )
    new.add_argument(
        "--allocate-next",
        action="store_true",
        help="Atomically allocate the next unused numeric prefix for the supplied slug.",
    )
    new.add_argument("--outcome", required=True)
    new.add_argument("--owned", action="append", required=True)
    new.add_argument("--shared", action="append", default=[])
    new.add_argument("--exclude", action="append", default=[])
    new.add_argument("--depends-on", action="append", default=[])
    new.add_argument("--integration-owner")
    new.add_argument("--complexity", default="medium", choices=sorted(COMPLEXITIES))
    new.add_argument(
        "--risk-trigger", action="append", default=[], choices=sorted(RISK_TRIGGERS)
    )
    new.add_argument("--upstream-sha")
    new.add_argument("--upstream-tree")
    new.add_argument("--upstream-ref")
    new.add_argument("--work-project-id")
    new.add_argument("--work-record-id")
    new.add_argument("--work-source-repository")
    new.add_argument("--work-source-number", type=int)
    new.add_argument("--work-source-kind", choices=sorted(WORK_SOURCE_KINDS))
    new.add_argument("--work-execution-owner")
    new.add_argument("--documentation-impact", choices=sorted(DOCUMENTATION_IMPACTS))
    new.add_argument("--base", default="main")

    validate = subparsers.add_parser(
        "validate", help="Validate active change claims and worktrees."
    )
    validate.add_argument(
        "--claims-only",
        action="store_true",
        help="Validate claim semantics without requiring unrelated active worktrees to exist locally.",
    )
    subparsers.add_parser(
        "check", help="Check the current diff against its declared scope."
    )
    subparsers.add_parser("list", help="List active and ready change claims.")
    cleanup = subparsers.add_parser("cleanup", help="Remove one clean merged worktree.")
    cleanup.add_argument("change_id")
    retire = subparsers.add_parser(
        "retire-orphan", help="Retire one clean unclaimed terminal worktree while preserving its branch."
    )
    retire.add_argument("change_id")
    retire.add_argument("--terminal-work-confirmed", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "new":
            target = create_change_worktree(
                args.repository,
                change_id=args.change_id,
                outcome=args.outcome,
                owned_paths=args.owned,
                shared_paths=args.shared,
                excluded_paths=args.exclude,
                dependencies=args.depends_on,
                integration_owner=args.integration_owner,
                work_management=(
                    None
                    if args.work_project_id is None
                    else {
                        "project_id": args.work_project_id,
                        "record_id": args.work_record_id,
                        "source_repository": args.work_source_repository,
                        "source_number": args.work_source_number,
                        "source_kind": args.work_source_kind,
                        "documentation_impact": args.documentation_impact,
                        "execution_owner": args.work_execution_owner,
                    }
                ),
                complexity=args.complexity,
                risk_triggers=args.risk_trigger,
                upstream_sha=args.upstream_sha,
                upstream_tree=args.upstream_tree,
                upstream_ref=args.upstream_ref,
                base=args.base,
                allocate_next=args.allocate_next,
            )
            print(json.dumps({"change_id": target.name, "worktree": str(target)}))
        elif args.command == "validate":
            claims = validate_repository(
                args.repository,
                require_active_worktrees=not args.claims_only,
            )
            compatibility = [
                {
                    "change_id": claim.change_id,
                    "warnings": list(claim.compatibility_warnings),
                }
                for claim in claims
                if claim.compatibility_warnings
            ]
            print(
                json.dumps(
                    {
                        "active_changes": sum(c.status in ACTIVE_STATUSES for c in claims),
                        "historical_compatibility_warnings": compatibility,
                        "orphaned_change_worktrees": orphaned_change_worktrees(args.repository),
                    }
                )
            )
        elif args.command == "check":
            changed = check_current_change(args.repository)
            print(json.dumps({"changed_paths": changed}))
        elif args.command == "list":
            claims = [
                claim.to_mapping()
                for claim in load_worktree_claims(repository_root(args.repository))
                if claim.status in ACTIVE_STATUSES
            ]
            print(json.dumps(claims, indent=2))
        elif args.command == "cleanup":
            result = cleanup_change_worktree(args.repository, args.change_id)
            print(json.dumps(result.to_mapping()))
        elif args.command == "retire-orphan":
            result = retire_closed_orphan_worktree(
                args.repository,
                args.change_id,
                terminal_work_confirmed=args.terminal_work_confirmed,
            )
            payload = result.to_mapping()
            payload.update({"branch_preserved": True, "terminal_work_confirmed": True})
            print(json.dumps(payload))
        else:
            parser.error(f"unsupported command: {args.command}")
    except ClaimError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
