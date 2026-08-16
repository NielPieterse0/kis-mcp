from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from ...discover.change_inspection_contracts import InspectChangeRequest
from ...discover.change_snapshot import collect_mutable_source_snapshot
from .contracts import ReviewEvidence

Runner = Callable[..., subprocess.CompletedProcess[str]]


class ChangeInspector(Protocol):
    def inspect(self, request: InspectChangeRequest) -> Any: ...


class EvidenceError(RuntimeError):
    """Raised when bounded local review evidence cannot be collected."""


def _inside(path: Path, boundary: Path) -> bool:
    try:
        return os.path.commonpath(
            [os.path.normcase(str(path)), os.path.normcase(str(boundary))]
        ) == os.path.normcase(str(boundary))
    except ValueError:
        return False


def _resolved_evidence_request(
    project: Path,
    request: InspectChangeRequest,
    identity: Any,
) -> InspectChangeRequest:
    if request.source in {"working_tree", "staged"}:
        return request
    if request.source == "commit":
        resolved = getattr(identity, "resolved_commit_ref", None)
        if not isinstance(resolved, str):
            raise EvidenceError("resolved review commit identity is unavailable")
        return InspectChangeRequest(path=str(project), source="commit", commit_ref=resolved)
    resolved_base = getattr(identity, "resolved_base_ref", None)
    resolved_head = getattr(identity, "resolved_head_ref", None)
    if not isinstance(resolved_base, str) or not isinstance(resolved_head, str):
        raise EvidenceError("resolved review range identity is unavailable")
    return InspectChangeRequest(
        path=str(project),
        source=request.source,
        base_ref=resolved_base,
        head_ref=resolved_head,
    )


class GitReviewEvidenceCollector:
    """Collect deterministic, source-bound Git evidence with explicit coverage."""

    def __init__(
        self,
        *,
        project_boundary: Path,
        max_chars: int,
        inspector: ChangeInspector,
        runner: Runner = subprocess.run,
    ) -> None:
        self.project_boundary = project_boundary.resolve()
        self.max_chars = max_chars
        self._inspector = inspector
        self._runner = runner

    def _git(self, project: Path, arguments: list[str]) -> str:
        completed = self._runner(
            ["git", *arguments],
            cwd=project,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode != 0:
            raise EvidenceError(f"Git evidence command failed: {' '.join(arguments)}")
        return completed.stdout or ""

    def _git_bytes(self, project: Path, arguments: tuple[str, ...]) -> bytes:
        completed = self._runner(
            ["git", *arguments],
            cwd=project,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise EvidenceError(f"Git evidence command failed: {' '.join(arguments)}")
        output = completed.stdout or b""
        return output.encode("utf-8") if isinstance(output, str) else bytes(output)

    def collect(
        self,
        path: Path,
        *,
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
    ) -> ReviewEvidence:
        project = path.resolve()
        if not project.is_dir():
            raise EvidenceError("review path must be an existing directory")
        if not _inside(project, self.project_boundary):
            raise EvidenceError("review path must remain inside the project boundary")

        request = InspectChangeRequest(
            path=str(project),
            source=source,
            commit_ref=commit_ref,
            base_ref=base_ref,
            head_ref=head_ref,
        )
        inspection = self._inspector.inspect(request)
        if not bool(getattr(inspection, "available", False)):
            raise EvidenceError("review source could not be inspected")
        identity = getattr(inspection, "change", None)
        fingerprint = getattr(identity, "fingerprint", None)
        if not isinstance(fingerprint, str) or len(fingerprint) != 64:
            raise EvidenceError("review source fingerprint is unavailable")
        evidence_request = _resolved_evidence_request(project, request, identity)

        records = tuple(getattr(inspection, "changed_files", ()))
        changed_files = tuple(item.path for item in records)
        sections: list[tuple[str, str]] = []
        evidence_fingerprint = fingerprint
        snapshot_mismatch = False
        if (
            request.source in {"working_tree", "staged"}
            and getattr(identity, "fingerprint_basis", None) == "evidence_snapshot"
        ):
            snapshot = collect_mutable_source_snapshot(
                project=project,
                source=request.source,
                records=records,
                run_git=lambda arguments: self._git_bytes(project, arguments),
            )
            evidence_fingerprint = snapshot.fingerprint
            snapshot_mismatch = evidence_fingerprint != fingerprint
            sections.extend((item.path, item.render_text()) for item in snapshot.sections)
        else:
            for item in records:
                sections.append((item.path, self._file_section(project, evidence_request, item)))

        agents_path = project / "AGENTS.md"
        instructions = ""
        if agents_path.is_file():
            try:
                instructions = agents_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise EvidenceError("AGENTS.md could not be read as UTF-8") from exc

        diagnostics: list[str] = []
        if bool(getattr(inspection, "truncated", False)):
            diagnostics.append("AGENT_SOURCE_INSPECTION_INCOMPLETE")
        if snapshot_mismatch:
            diagnostics.append("AGENT_EVIDENCE_SOURCE_CHANGED")
        final_inspection = self._inspector.inspect(request)
        final_identity = getattr(final_inspection, "change", None)
        final_fingerprint = getattr(final_identity, "fingerprint", None)
        if (
            not bool(getattr(final_inspection, "available", False))
            or bool(getattr(final_inspection, "truncated", False))
            or final_fingerprint != fingerprint
        ):
            diagnostics.append("AGENT_EVIDENCE_SOURCE_CHANGED")
        included: list[str] = []
        omitted: list[str] = list(changed_files)
        include_instructions = bool(instructions)

        def render() -> str:
            manifest = {
                "source": request.source,
                "source_fingerprint": evidence_fingerprint,
                "commit_ref": evidence_request.commit_ref,
                "base_ref": evidence_request.base_ref,
                "head_ref": evidence_request.head_ref,
                "changed_files": list(changed_files),
                "included_files": list(included),
                "omitted_files": list(omitted),
                "instructions_included": include_instructions,
                "complete": not diagnostics and not omitted and (not instructions or include_instructions),
                "diagnostics": list(diagnostics),
            }
            parts = ["# Review evidence manifest\n" + json.dumps(manifest, sort_keys=True, separators=(",", ":"))]
            if include_instructions and instructions:
                parts.append("# Repository instructions\n" + instructions.rstrip())
            for file_path, section in sections:
                if file_path in included:
                    parts.append(section.rstrip())
            return "\n\n".join(parts).rstrip()

        if include_instructions and len(render()) > self.max_chars:
            include_instructions = False
            diagnostics.append("AGENT_REPOSITORY_INSTRUCTIONS_OMITTED")
        for file_path, _ in sections:
            included.append(file_path)
            omitted.remove(file_path)
            if len(render()) > self.max_chars:
                included.pop()
                omitted.insert(0, file_path)
        content = render()
        if len(content) > self.max_chars:
            raise EvidenceError("review evidence metadata exceeds configured budget")
        complete = not diagnostics and not omitted and (not instructions or include_instructions)
        if omitted:
            diagnostics.append("AGENT_EVIDENCE_FILES_OMITTED")
            content = render()
        return ReviewEvidence(
            content=content,
            source=request.source,
            source_fingerprint=evidence_fingerprint,
            changed_files=changed_files,
            included_files=tuple(included),
            omitted_files=tuple(omitted),
            complete=complete,
            commit_ref=evidence_request.commit_ref,
            base_ref=evidence_request.base_ref,
            head_ref=evidence_request.head_ref,
            diagnostics=tuple(dict.fromkeys(diagnostics)),
        )

    def _file_section(self, project: Path, request: InspectChangeRequest, item: Any) -> str:
        paths = [item.path]
        previous = getattr(item, "previous_path", None)
        if previous:
            paths.append(previous)
        header = {
            "path": item.path,
            "previous_path": previous,
            "staged_status": getattr(item, "staged_status", None),
            "worktree_status": getattr(item, "worktree_status", None),
            "untracked": bool(getattr(item, "untracked", False)),
        }
        patches: list[str] = []
        if request.source == "working_tree":
            if header["untracked"]:
                target = project / item.path
                try:
                    body = target.read_text(encoding="utf-8")
                except (OSError, UnicodeError):
                    body = "[untracked file is not UTF-8 text]"
                patches.append("# Untracked file content\n" + body)
            else:
                patches.append("# Unstaged patch\n" + self._git(project, ["diff", "--no-ext-diff", "--no-textconv", "--unified=3", "--", *paths]))
                patches.append("# Staged patch\n" + self._git(project, ["diff", "--cached", "--no-ext-diff", "--no-textconv", "--unified=3", "--", *paths]))
        elif request.source == "staged":
            patches.append(self._git(project, ["diff", "--cached", "--no-ext-diff", "--no-textconv", "--unified=3", "--", *paths]))
        elif request.source == "commit":
            assert request.commit_ref is not None
            patches.append(self._git(project, ["show", "--format=", "--no-ext-diff", "--no-textconv", "--unified=3", "--end-of-options", request.commit_ref, "--", *paths]))
        else:
            assert request.base_ref is not None and request.head_ref is not None
            patches.append(self._git(project, ["diff", "--no-ext-diff", "--no-textconv", "--unified=3", "--end-of-options", f"{request.base_ref}...{request.head_ref}", "--", *paths]))
        return "# Changed file\n" + json.dumps(header, sort_keys=True, separators=(",", ":")) + "\n" + "\n".join(patches).rstrip()


__all__ = ["ChangeInspector", "EvidenceError", "GitReviewEvidenceCollector"]
