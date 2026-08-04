from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


ChangeStatus = str
Diagnostic = Mapping[str, str]


@dataclass(frozen=True, slots=True)
class ChangePathRecord:
    path: str
    previous_path: str | None = None
    staged_status: ChangeStatus | None = None
    worktree_status: ChangeStatus | None = None
    untracked: bool = False

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "previous_path": self.previous_path,
            "staged_status": self.staged_status,
            "worktree_status": self.worktree_status,
            "untracked": self.untracked,
        }


@dataclass(frozen=True, slots=True)
class ChangeSummary:
    total: int = 0
    staged: int = 0
    unstaged: int = 0
    untracked: int = 0
    renamed: int = 0
    copied: int = 0
    deleted: int = 0
    conflicted: int = 0

    def to_json_dict(self) -> dict[str, int]:
        return {
            "total": self.total,
            "staged": self.staged,
            "unstaged": self.unstaged,
            "untracked": self.untracked,
            "renamed": self.renamed,
            "copied": self.copied,
            "deleted": self.deleted,
            "conflicted": self.conflicted,
        }


@dataclass(frozen=True, slots=True)
class LocalChangeInventory:
    project_path: str
    repository_root: str | None
    changes: tuple[ChangePathRecord, ...] = ()
    summary: ChangeSummary = field(default_factory=ChangeSummary)
    diagnostics: tuple[Diagnostic, ...] = ()
    truncated: bool = False
    schema_version: int = 1
    source: str = "local_git"

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source": self.source,
            "project_path": self.project_path,
            "repository_root": self.repository_root,
            "changes": [change.to_json_dict() for change in self.changes],
            "summary": self.summary.to_json_dict(),
            "diagnostics": [dict(item) for item in self.diagnostics],
            "truncated": self.truncated,
        }


__all__ = [
    "ChangePathRecord",
    "ChangeStatus",
    "ChangeSummary",
    "Diagnostic",
    "LocalChangeInventory",
]
