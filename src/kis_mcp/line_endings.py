from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any


_TEXT_MUTATIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "write_file": ("path", ("content",)),
    "edit_block": ("file_path", ("old_string", "new_string")),
}


class RepositoryLineEndingNormalizer:
    """Normalize provider text mutations to the target worktree's Git EOL rule."""

    def __init__(self, *, project_boundary: str | Path) -> None:
        self.project_boundary = Path(project_boundary).resolve(strict=False)

    def normalize(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        normalized = dict(arguments or {})
        contract = _TEXT_MUTATIONS.get(tool_name.casefold())
        if contract is None:
            return normalized

        path_key, text_keys = contract
        target_value = normalized.get(path_key)
        if not isinstance(target_value, str) or not target_value.strip():
            return normalized

        text_values = [normalized.get(key) for key in text_keys]
        if not any(
            isinstance(value, str) and ("\n" in value or "\r" in value)
            for value in text_values
        ):
            return normalized

        target = self._absolute_target(target_value)
        if target is None:
            return normalized
        eol = self._effective_git_eol(target)
        if eol is None:
            return normalized

        for key in text_keys:
            value = normalized.get(key)
            if isinstance(value, str):
                normalized[key] = self._normalize_text(value, eol=eol)
        return normalized

    def _absolute_target(self, value: str) -> Path | None:
        target = Path(value)
        if not target.is_absolute():
            return None
        resolved = target.resolve(strict=False)
        try:
            resolved.relative_to(self.project_boundary)
        except ValueError:
            return None
        return resolved

    def _effective_git_eol(self, target: Path) -> str | None:
        repository = self._find_git_worktree(target)
        if repository is None:
            return None
        try:
            relative = target.relative_to(repository)
        except ValueError:
            return None

        environment = os.environ.copy()
        environment["GIT_OPTIONAL_LOCKS"] = "0"
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
            environment.pop(key, None)
        try:
            completed = subprocess.run(
                ["git", "check-attr", "-z", "text", "eol", "--", str(relative)],
                cwd=repository,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if completed.returncode != 0:
            return None

        fields = completed.stdout.split("\0")
        attributes: dict[str, str] = {}
        for index in range(0, len(fields) - 2, 3):
            name = fields[index + 1]
            value = fields[index + 2]
            if name:
                attributes[name] = value.casefold()
        if attributes.get("text") == "unset":
            return None
        eol = attributes.get("eol")
        return eol if eol in {"lf", "crlf"} else None

    def _find_git_worktree(self, target: Path) -> Path | None:
        current = target.parent
        while True:
            try:
                current.relative_to(self.project_boundary)
            except ValueError:
                return None
            if (current / ".git").exists():
                return current
            if current == self.project_boundary:
                return None
            parent = current.parent
            if parent == current:
                return None
            current = parent

    @staticmethod
    def _normalize_text(value: str, *, eol: str) -> str:
        lf = value.replace("\r\n", "\n").replace("\r", "\n")
        return lf if eol == "lf" else lf.replace("\n", "\r\n")
