from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any, Protocol

from .change_analysis import AnalyzeChangeRequest, AnalyzeChangeResponse, AnalyzeChangeService
from .change_contracts import ChangePathRecord, LocalChangeInventory
from .change_inspection_contracts import (
    ChangeIdentity,
    ChangeImpactSummary,
    ChangeUnknown,
    ChangeVerificationHandoff,
    ChangedFile,
    InspectChangeRequest,
    InspectChangeResponse,
)
from .change_targets import ChangeTargetInventory
from .impact_graph import ImpactGraphService
from .intelligence import ProjectIntelligenceService


class LocalChangeReader(Protocol):
    def inspect_local_changes(self, project_path: str) -> LocalChangeInventory: ...


class TargetChangeReader(Protocol):
    def inspect_change_target(self, request: InspectChangeRequest) -> ChangeTargetInventory: ...


_CODE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".swift",
    ".ts",
    ".tsx",
}

_DOCUMENTATION_NAMES = {
    "agents.md",
    "changelog.md",
    "contributing.md",
    "readme.md",
    "security.md",
}
_CONFIGURATION_NAMES = {
    ".editorconfig",
    ".gitignore",
    "dockerfile",
    "makefile",
    "package.json",
    "pyproject.toml",
    "tox.ini",
    "uv.lock",
}
_CONFIGURATION_EXTENSIONS = {
    ".ini",
    ".json",
    ".lock",
    ".toml",
    ".yaml",
    ".yml",
}
_CONTRACT_EXTENSIONS = {".graphql", ".gql", ".proto"}
_FATAL_DIAGNOSTICS = {
    "CHANGE_TARGET_READER_UNAVAILABLE",
    "CHANGE_SOURCE_FINGERPRINT_UNAVAILABLE",
    "CHANGE_SOURCE_CHANGED_DURING_INSPECTION",
    "GIT_CHANGE_READ_FAILED",
    "GIT_EXECUTION_FAILED",
    "GIT_METADATA_ENCODING_INVALID",
    "GIT_METADATA_INVALID",
    "GIT_METADATA_OUTSIDE_BOUNDARY",
    "GIT_METADATA_TARGET_MISSING",
    "GIT_METADATA_TARGET_NOT_DIRECTORY",
    "GIT_METADATA_TOO_LARGE",
    "GIT_METADATA_UNSAFE",
    "GIT_NOT_REPOSITORY",
    "GIT_REPOSITORY_OUTSIDE_BOUNDARY",
    "GIT_TARGET_INVALID",
    "GIT_TIMEOUT",
    "GIT_UNAVAILABLE",
}
_HANDOFFS = (
    ("source", "verification.source", "Run verification applicable to changed source files."),
    ("test", "verification.tests", "Run the affected test verification workflow."),
    ("contract", "verification.contracts", "Run contract and schema verification."),
    (
        "configuration",
        "verification.configuration",
        "Run configuration and integration verification.",
    ),
    ("policy", "verification.policy", "Run governance and policy verification."),
    (
        "documentation",
        "verification.documentation",
        "Run documentation validation and drift checks.",
    ),
)


class InspectChangeService:
    def __init__(
        self,
        reader: LocalChangeReader | TargetChangeReader,
        *,
        intelligence_service: ProjectIntelligenceService | None = None,
    ) -> None:
        self._reader = reader
        authority = getattr(reader, "authority", None)
        settings = getattr(reader, "settings", None)
        self._analysis_service = (
            AnalyzeChangeService(
                change_service=self,
                impact_service=ImpactGraphService(
                    boundary=authority.boundary,
                    settings=settings,
                    intelligence_service=intelligence_service,
                ),
                max_changes=settings.limits.max_files,
                max_task_terms=settings.limits.max_evidence,
            )
            if authority is not None and settings is not None
            else None
        )

    def analyze(self, request: AnalyzeChangeRequest) -> AnalyzeChangeResponse:
        if self._analysis_service is None:
            raise ValueError("analyze_change is unavailable for this change reader")
        return self._analysis_service.analyze(request)

    def inspect(self, request: InspectChangeRequest) -> InspectChangeResponse:
        inventory = self._read_inventory(request)
        available = _inventory_available(inventory)
        changed_files = tuple(_changed_file(record) for record in inventory.changes)
        categories = {
            category: tuple(
                item.path for item in changed_files if category in item.categories
            )
            for category in (
                "test",
                "contract",
                "documentation",
                "configuration",
                "policy",
            )
        }
        unknowns = (
            _available_unknowns()
            if available
            else (
                ChangeUnknown(
                    code="CHANGE_REPOSITORY_EVIDENCE_UNAVAILABLE",
                    reason="Local repository change evidence is unavailable.",
                ),
            )
        )
        confidence = (
            "low"
            if not available
            else "medium"
            if inventory.truncated or inventory.diagnostics
            else "high"
        )
        return InspectChangeResponse(
            available=available,
            project_path=inventory.project_path,
            repository_root=inventory.repository_root,
            change=ChangeIdentity(
                source=request.source,
                fingerprint=_fingerprint(inventory),
                commit_ref=request.commit_ref,
                base_ref=request.base_ref,
                head_ref=request.head_ref,
                resolved_commit_ref=getattr(inventory, "resolved_commit_ref", None),
                resolved_base_ref=getattr(inventory, "resolved_base_ref", None),
                resolved_head_ref=getattr(inventory, "resolved_head_ref", None),
                fingerprint_basis=(
                    "evidence_snapshot"
                    if request.source in {"working_tree", "staged"}
                    else "immutable_ref"
                ),
            ),
            changed_files=changed_files,
            affected_scopes=_affected_scopes(inventory.changes),
            changed_tests=categories["test"],
            contract_paths=categories["contract"],
            documentation_paths=categories["documentation"],
            configuration_paths=categories["configuration"],
            policy_paths=categories["policy"],
            impact_summary=_impact_summary(changed_files),
            diagnostics=inventory.diagnostics,
            unknowns=unknowns,
            confidence=confidence,
            truncated=inventory.truncated,
            verification_handoffs=_verification_handoffs(changed_files),
            source=request.source,
        )

    def _read_inventory(
        self,
        request: InspectChangeRequest,
    ) -> LocalChangeInventory | ChangeTargetInventory:
        if request.source == "working_tree":
            local_method = getattr(self._reader, "inspect_local_changes", None)
            if callable(local_method):
                return local_method(request.path)
        target_method = getattr(self._reader, "inspect_change_target", None)
        if callable(target_method):
            return target_method(request)
        return ChangeTargetInventory(
            project_path=request.path,
            repository_root=None,
            source=request.source,
            commit_ref=request.commit_ref,
            base_ref=request.base_ref,
            head_ref=request.head_ref,
            diagnostics=(
                {
                    "code": "CHANGE_TARGET_READER_UNAVAILABLE",
                    "message": "The configured reader does not support this change target.",
                },
            ),
        )


def _inventory_available(inventory: LocalChangeInventory | ChangeTargetInventory) -> bool:
    if inventory.repository_root is None:
        return False
    return all(
        diagnostic.get("code") not in _FATAL_DIAGNOSTICS
        for diagnostic in inventory.diagnostics
    )


def _changed_file(record: ChangePathRecord) -> ChangedFile:
    return ChangedFile(
        path=record.path,
        previous_path=record.previous_path,
        staged_status=record.staged_status,
        worktree_status=record.worktree_status,
        untracked=record.untracked,
        categories=(_classify_path(record.path),),
    )


def _fingerprint(inventory: Any) -> str:
    source_fingerprint = getattr(inventory, "source_fingerprint", None)
    if isinstance(source_fingerprint, str) and len(source_fingerprint) == 64:
        return source_fingerprint
    canonical = json.dumps(
        inventory.to_json_dict(),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _classify_path(path: str) -> str:
    normalized = _normalize_path(path)
    lowered = normalized.casefold()
    parts = tuple(part for part in lowered.split("/") if part)
    first = parts[0] if parts else ""
    name = parts[-1] if parts else lowered
    suffix = _suffix(name)

    if (
        first in {"test", "tests", "spec", "specs"}
        or name.startswith("test_")
        or name.endswith(("_test.py", ".test.js", ".test.ts", ".spec.js", ".spec.ts"))
    ):
        return "test"
    if (
        first in {"contract", "contracts", "schema", "schemas"}
        or name.endswith(".schema.json")
        or suffix in _CONTRACT_EXTENSIONS
        or name.startswith(("openapi.", "asyncapi."))
    ):
        return "contract"
    if (
        first in {"doc", "docs", "documentation"}
        or name in _DOCUMENTATION_NAMES
        or suffix in {".adoc", ".md", ".rst"}
    ):
        return "documentation"
    if first in {"policy", "policies"}:
        return "policy"
    if (
        first in {".github", "config", "configs", "configuration", "settings"}
        or name in _CONFIGURATION_NAMES
        or suffix in _CONFIGURATION_EXTENSIONS
    ):
        return "configuration"
    if first in {"app", "apps", "lib", "libs", "package", "packages", "service", "services", "src"}:
        return "source"
    if suffix in _CODE_EXTENSIONS:
        return "source"
    return "other"


def _affected_scopes(records: Iterable[ChangePathRecord]) -> tuple[str, ...]:
    scopes: set[str] = set()
    for record in records:
        for path in (record.path, record.previous_path):
            if path is None:
                continue
            normalized = _normalize_path(path)
            scopes.add(normalized.split("/", 1)[0] if "/" in normalized else ".")
    return tuple(sorted(scopes, key=lambda value: (value == ".", value.casefold(), value)))


def _impact_summary(changed_files: tuple[ChangedFile, ...]) -> ChangeImpactSummary:
    counts = {
        category: sum(category in item.categories for item in changed_files)
        for category in (
            "source",
            "test",
            "contract",
            "documentation",
            "configuration",
            "policy",
            "other",
        )
    }
    return ChangeImpactSummary(
        total_files=len(changed_files),
        source_files=counts["source"],
        test_files=counts["test"],
        contract_files=counts["contract"],
        documentation_files=counts["documentation"],
        configuration_files=counts["configuration"],
        policy_files=counts["policy"],
        other_files=counts["other"],
    )


def _verification_handoffs(
    changed_files: tuple[ChangedFile, ...],
) -> tuple[ChangeVerificationHandoff, ...]:
    handoffs: list[ChangeVerificationHandoff] = []
    for category, verification_id, reason in _HANDOFFS:
        paths = tuple(
            item.path for item in changed_files if category in item.categories
        )
        if not paths:
            continue
        handoffs.append(
            ChangeVerificationHandoff(
                handoff_id=f"ho-change-{category}",
                verification_id=verification_id,
                category=category,
                reason=reason,
                paths=paths,
            )
        )
    return tuple(handoffs)


def _available_unknowns() -> tuple[ChangeUnknown, ...]:
    return (
        ChangeUnknown(
            code="CHANGE_DEPENDANT_IMPACT_UNAVAILABLE",
            reason="Dependant impact mapping is not available in this slice.",
        ),
        ChangeUnknown(
            code="CHANGE_SYMBOL_IMPACT_UNAVAILABLE",
            reason="Symbol impact is not available in this slice.",
        ),
    )


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def _suffix(name: str) -> str:
    marker = name.rfind(".")
    return name[marker:] if marker >= 0 else ""


__all__ = [
    "InspectChangeService",
    "LocalChangeReader",
    "TargetChangeReader",
]
