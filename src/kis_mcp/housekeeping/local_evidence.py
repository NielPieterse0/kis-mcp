from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class GovernedWorkLink:
    change_id: str
    scope_path: str
    source_repository: str
    source_number: int
    source_kind: str
    status: str
    complexity: str | None
    risk_triggers: tuple[str, ...]

    @property
    def source_key(self) -> tuple[str, int, str]:
        return (
            self.source_repository.casefold(),
            self.source_number,
            self.source_kind,
        )


def _scope_link(root: Path, path: Path) -> GovernedWorkLink | None:
    try:
        document: Any = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(document, dict):
        return None
    work = document.get("work_management")
    if not isinstance(work, dict):
        return None
    repository = work.get("source_repository")
    number = work.get("source_number")
    kind = work.get("source_kind")
    change_id = document.get("change_id")
    if (
        not isinstance(repository, str)
        or not repository.strip()
        or not isinstance(number, int)
        or isinstance(number, bool)
        or number <= 0
        or kind not in {"issue", "pull_request"}
        or not isinstance(change_id, str)
    ):
        return None
    raw_triggers = document.get("risk_triggers", [])
    triggers = tuple(
        sorted(item.strip() for item in raw_triggers if isinstance(item, str) and item.strip())
    )
    return GovernedWorkLink(
        change_id=change_id,
        scope_path=str(path.relative_to(root)).replace("\\", "/"),
        source_repository=repository.strip(),
        source_number=number,
        source_kind=kind,
        status=str(document.get("status", "unknown")),
        complexity=(str(document["complexity"]) if document.get("complexity") else None),
        risk_triggers=triggers,
    )


def governed_work_links(repository_root: Path) -> tuple[GovernedWorkLink, ...]:
    root = repository_root.resolve()
    changes = root / ".work" / "changes"
    if not changes.is_dir():
        return ()
    links = tuple(
        link
        for path in sorted(changes.glob("*/scope.json"))
        for link in (_scope_link(root, path),)
        if link is not None
    )
    return tuple(
        sorted(
            links,
            key=lambda item: (
                item.source_repository.casefold(),
                item.source_number,
                item.change_id,
            ),
        )
    )


__all__ = ["GovernedWorkLink", "governed_work_links"]
