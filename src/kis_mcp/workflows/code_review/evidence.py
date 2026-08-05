from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

Runner = Callable[..., subprocess.CompletedProcess[str]]


class EvidenceError(RuntimeError):
    """Raised when bounded local review evidence cannot be collected."""


def _inside(path: Path, boundary: Path) -> bool:
    try:
        return os.path.commonpath(
            [os.path.normcase(str(path)), os.path.normcase(str(boundary))]
        ) == os.path.normcase(str(boundary))
    except ValueError:
        return False


class GitReviewEvidenceCollector:
    """Collect bounded repository instructions and current Git diff evidence."""

    def __init__(
        self,
        *,
        project_boundary: Path,
        max_chars: int,
        runner: Runner = subprocess.run,
    ) -> None:
        self.project_boundary = project_boundary.resolve()
        self.max_chars = max_chars
        self._runner = runner

    def _git(self, project: Path, arguments: list[str]) -> str:
        completed = self._runner(
            ["git", *arguments],
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise EvidenceError(
                f"Git evidence command failed: {' '.join(arguments)}"
            )
        return completed.stdout or ""

    def collect(self, path: Path) -> str:
        project = path.resolve()
        if not project.is_dir():
            raise EvidenceError("review path must be an existing directory")
        if not _inside(project, self.project_boundary):
            raise EvidenceError("review path must remain inside the project boundary")

        instructions = ""
        agents_path = project / "AGENTS.md"
        if agents_path.is_file():
            try:
                instructions = agents_path.read_text(encoding="utf-8")[:20000]
            except (OSError, UnicodeError) as exc:
                raise EvidenceError("AGENTS.md could not be read as UTF-8") from exc

        sections = [
            "# Repository instructions\n" + (instructions or "[none]"),
            "# Git status\n" + self._git(project, ["status", "--short"]),
            "# Unstaged diff\n"
            + self._git(project, ["diff", "--no-ext-diff", "--unified=3"]),
            "# Staged diff\n"
            + self._git(
                project,
                ["diff", "--cached", "--no-ext-diff", "--unified=3"],
            ),
        ]
        evidence = "\n\n".join(sections).rstrip()
        marker = "\n[evidence truncated]"
        if len(evidence) > self.max_chars:
            evidence = evidence[: self.max_chars - len(marker)] + marker
        return evidence


__all__ = ["EvidenceError", "GitReviewEvidenceCollector"]
