from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ReviewEvidence:
    content: str
    source: str
    source_fingerprint: str
    changed_files: tuple[str, ...]
    included_files: tuple[str, ...]
    omitted_files: tuple[str, ...]
    complete: bool
    ignored_files: tuple[str, ...] = ()
    projector: str = "changed-code-tests"
    commit_ref: str | None = None
    base_ref: str | None = None
    head_ref: str | None = None
    diagnostics: tuple[str, ...] = ()

    def provenance(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "source": self.source,
            "source_fingerprint": self.source_fingerprint,
            "changed_files": list(self.changed_files),
            "included_files": list(self.included_files),
            "omitted_files": list(self.omitted_files),
            "ignored_files": list(self.ignored_files),
            "evidence_projector": self.projector,
            "evidence_complete": self.complete,
            "evidence_chars": len(self.content),
        }
        for name in ("commit_ref", "base_ref", "head_ref"):
            value = getattr(self, name)
            if value is not None:
                result[name] = value
        return result


class ReviewBackend(Protocol):
    name: str

    def available(self) -> bool: ...

    def review(
        self,
        project_path: Path,
        prompt: str,
        *,
        timeout_seconds: float | None = None,
    ) -> str: ...


class EvidenceCollector(Protocol):
    def collect(
        self,
        path: Path,
        *,
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
        review_type: str = "code-quality",
    ) -> ReviewEvidence: ...


__all__ = ["EvidenceCollector", "ReviewBackend", "ReviewEvidence"]
