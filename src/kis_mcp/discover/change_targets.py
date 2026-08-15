from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .change_contracts import ChangePathRecord
from .change_inspection_contracts import InspectChangeRequest


@dataclass(frozen=True, slots=True)
class ChangeTargetInventory:
    project_path: str
    repository_root: str | None
    source: str
    changes: tuple[ChangePathRecord, ...] = ()
    commit_ref: str | None = None
    base_ref: str | None = None
    head_ref: str | None = None
    resolved_commit_ref: str | None = None
    resolved_base_ref: str | None = None
    resolved_head_ref: str | None = None
    diagnostics: tuple[Mapping[str, str], ...] = ()
    truncated: bool = False
    source_fingerprint: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "project_path": self.project_path,
            "repository_root": self.repository_root,
            "source": self.source,
            "changes": [item.to_json_dict() for item in self.changes],
            "diagnostics": [dict(item) for item in self.diagnostics],
            "truncated": self.truncated,
        }
        for name in ("commit_ref", "base_ref", "head_ref"):
            value = getattr(self, name)
            if value is not None:
                result[name] = value
        return result


def build_target_arguments(request: InspectChangeRequest) -> tuple[str, ...]:
    common = (
        "--no-ext-diff",
        "--no-textconv",
    )
    output = (
        "--name-status",
        "-z",
        "--find-renames",
        "--find-copies",
    )
    if request.source == "staged":
        return ("diff", *common, "--cached", *output)
    if request.source == "commit":
        assert request.commit_ref is not None
        return (
            "diff-tree",
            "--root",
            "--no-commit-id",
            "-r",
            *common,
            *output,
            "--end-of-options",
            request.commit_ref,
            "--",
        )
    if request.source in {"range", "branch"}:
        assert request.base_ref is not None and request.head_ref is not None
        return (
            "diff",
            *common,
            *output,
            "--end-of-options",
            f"{request.base_ref}...{request.head_ref}",
            "--",
        )
    raise ValueError("target source requires the working-tree reader or is unsupported")


def parse_name_status(output: bytes) -> tuple[ChangePathRecord, ...]:
    fields = _complete_nul_fields(output)
    records: list[ChangePathRecord] = []
    index = 0
    while index < len(fields):
        raw_status = fields[index]
        index += 1
        marker = raw_status[:1].upper()
        status = _normalize_status(marker)
        if marker in {"C", "R"}:
            if index + 1 >= len(fields):
                break
            previous_path = fields[index]
            path = fields[index + 1]
            index += 2
        else:
            if index >= len(fields):
                break
            previous_path = None
            path = fields[index]
            index += 1
        if path:
            records.append(
                ChangePathRecord(
                    path=path,
                    previous_path=previous_path,
                    staged_status=status,
                )
            )
    return tuple(
        sorted(records, key=lambda item: (item.path.casefold(), item.path))
    )


def _complete_nul_fields(output: bytes) -> tuple[str, ...]:
    if not output or not output.endswith(b"\x00"):
        return ()
    return tuple(
        field.decode("utf-8", errors="replace") for field in output[:-1].split(b"\x00")
    )


def _normalize_status(marker: str) -> str:
    return {
        "A": "added",
        "C": "copied",
        "D": "deleted",
        "M": "modified",
        "R": "renamed",
        "T": "type_changed",
        "U": "unmerged",
    }.get(marker, "unknown")


__all__ = [
    "ChangeTargetInventory",
    "build_target_arguments",
    "parse_name_status",
]
