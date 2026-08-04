from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Protocol

from .change_contracts import ChangePathRecord, LocalChangeInventory
from .change_inspection_contracts import (
    ChangeIdentity,
    ChangeImpactSummary,
    ChangeUnknown,
    ChangedFile,
    InspectChangeRequest,
    InspectChangeResponse,
    WORKING_TREE_SOURCE,
)


class LocalChangeReader(Protocol):
    def inspect_local_changes(self, project_path: str) -> LocalChangeInventory: ...


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
    "GIT_TIMEOUT",
    "GIT_UNAVAILABLE",
}


class InspectChangeService:
    def __init__(self, reader: LocalChangeReader) -> None:
        self._reader = reader

    def inspect(self, request: InspectChangeRequest) -> InspectChangeResponse:
        inventory = self._reader.inspect_local_changes(request.path)
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
                source=WORKING_TREE_SOURCE,
                fingerprint=_fingerprint(inventory),
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
        )


def _inventory_available(inventory: LocalChangeInventory) -> bool:
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


def _fingerprint(inventory: LocalChangeInventory) -> str:
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
        ChangeUnknown(
            code="CHANGE_VERIFICATION_MAPPING_UNAVAILABLE",
            reason="Verification impact mapping is not available in this slice.",
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


__all__ = ["InspectChangeService", "LocalChangeReader"]
