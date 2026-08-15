from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

GitBytesRunner = Callable[[tuple[str, ...]], bytes]
FileBytesReader = Callable[[Path], bytes]


@dataclass(frozen=True, slots=True)
class MutableSnapshotSection:
    path: str
    header: bytes
    payload: bytes

    def render_text(self) -> str:
        return (
            "# Changed file\n"
            + self.header.decode("utf-8")
            + "\n"
            + self.payload.decode("utf-8", errors="replace").rstrip()
        )


@dataclass(frozen=True, slots=True)
class MutableSourceSnapshot:
    fingerprint: str
    sections: tuple[MutableSnapshotSection, ...]


def collect_mutable_source_snapshot(
    *,
    project: Path,
    source: str,
    records: tuple[Any, ...],
    run_git: GitBytesRunner,
    read_file: FileBytesReader | None = None,
) -> MutableSourceSnapshot:
    if source not in {"working_tree", "staged"}:
        raise ValueError("mutable source snapshot supports working_tree or staged only")
    read_file = read_file or (lambda path: path.read_bytes())
    head = run_git(("rev-parse", "HEAD")).strip()
    sections: list[MutableSnapshotSection] = []
    for item in records:
        paths = [item.path]
        previous = getattr(item, "previous_path", None)
        if previous:
            paths.append(previous)
        header = json.dumps(
            {
                "path": item.path,
                "previous_path": previous,
                "staged_status": getattr(item, "staged_status", None),
                "worktree_status": getattr(item, "worktree_status", None),
                "untracked": bool(getattr(item, "untracked", False)),
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if source == "working_tree":
            if bool(getattr(item, "untracked", False)):
                payload = b"# Untracked file content\n" + read_file(project / item.path)
            else:
                unstaged = run_git(
                    (
                        "diff",
                        "--no-ext-diff",
                        "--no-textconv",
                        "--unified=3",
                        "--",
                        *paths,
                    )
                )
                staged = run_git(
                    (
                        "diff",
                        "--cached",
                        "--no-ext-diff",
                        "--no-textconv",
                        "--unified=3",
                        "--",
                        *paths,
                    )
                )
                payload = b"# Unstaged patch\n" + unstaged + b"\n# Staged patch\n" + staged
        else:
            payload = run_git(
                (
                    "diff",
                    "--cached",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--unified=3",
                    "--",
                    *paths,
                )
            )
        sections.append(MutableSnapshotSection(path=item.path, header=header, payload=payload))

    digest = hashlib.sha256()
    _update(digest, b"source", source.encode("ascii"))
    _update(digest, b"head", head)
    for section in sections:
        _update(digest, b"path", section.path.encode("utf-8"))
        _update(digest, b"header", section.header)
        _update(digest, b"payload", section.payload)
    return MutableSourceSnapshot(fingerprint=digest.hexdigest(), sections=tuple(sections))


def _update(digest: Any, label: bytes, value: bytes) -> None:
    digest.update(len(label).to_bytes(4, "big"))
    digest.update(label)
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


__all__ = ["MutableSnapshotSection", "MutableSourceSnapshot", "collect_mutable_source_snapshot"]
