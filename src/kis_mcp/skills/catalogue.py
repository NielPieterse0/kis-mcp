from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Iterable

from .config import SkillsConfig
from .errors import SkillsError
from .models import (
    SkillCard,
    SkillEvaluationEvidence,
    SkillEvaluationResponse,
    SkillFileMatch,
    SkillFileResponse,
    SkillFileSearchResponse,
    SkillListResponse,
    SkillLoadResponse,
    SkillRefreshResponse,
    SkillSearchResponse,
)


_SEARCH_TERM = re.compile(r"[a-z0-9-]+")
_FRONTMATTER_KEY = re.compile(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$")


@dataclass(frozen=True, slots=True)
class _FileEntry:
    path: str
    group: str
    size: int
    sha256: str
    content: str | None


@dataclass(frozen=True, slots=True)
class _SkillEntry:
    id: str
    source_directory: str
    summary: str
    category: str
    capabilities: tuple[str, ...]
    status: str
    content: str
    content_hash: str
    files: tuple[_FileEntry, ...]
    reference_group_counts: MappingProxyType[str, int]


@dataclass(frozen=True, slots=True)
class _Snapshot:
    snapshot_id: str
    skills: tuple[_SkillEntry, ...]


@dataclass(frozen=True, slots=True)
class ProposedSkillCreate:
    skill_id: str
    content: str
    after_sha256: str


@dataclass(frozen=True, slots=True)
class ProposedSkillReplacement:
    skill_id: str
    relative_path: str
    target_path: Path
    current_content: str
    content: str
    before_sha256: str
    after_sha256: str


class SkillCatalogue:
    """Deterministic, bounded catalogue over one configured Skills root."""

    def __init__(self, config: SkillsConfig) -> None:
        self.config = config
        self.root = config.root.resolve(strict=True)
        if not self.root.is_dir():
            raise SkillsError("SKILLS_ROOT_INVALID", "Skills root must be a directory")
        self._assert_no_link(self.root)
        self._snapshot: _Snapshot | None = None
        self.refresh_skills()

    @property
    def snapshot_id(self) -> str:
        if self._snapshot is None:
            raise SkillsError("SKILLS_SNAPSHOT_MISSING", "No active Skills snapshot")
        return self._snapshot.snapshot_id

    @property
    def skill_count(self) -> int:
        return len(self._active())

    def refresh_skills(self) -> SkillRefreshResponse:
        accepted: list[_SkillEntry] = []
        problems: list[str] = []
        canonical_sources: dict[str, str] = {}
        for path in sorted(self.root.iterdir(), key=lambda item: item.name.casefold()):
            if path.name.startswith("."):
                continue
            try:
                self._assert_no_link(path)
                if not path.is_dir():
                    raise SkillsError(
                        "SKILLS_SOURCE_INVALID", "Skill source must be a directory"
                    )
                entry = self._build_entry(path)
                previous = canonical_sources.get(entry.id)
                if previous is not None:
                    raise SkillsError(
                        "SKILLS_ID_DUPLICATE",
                        f"Canonical skill ID duplicates source {previous}",
                    )
                canonical_sources[entry.id] = path.name
                accepted.append(entry)
            except SkillsError as exc:
                problems.append(f"{path.name}: {exc}")
        if problems:
            raise SkillsError(
                "SKILLS_REFRESH_REJECTED",
                "; ".join(problems),
            )

        accepted.sort(key=lambda item: item.id)
        snapshot_payload = [self._fingerprint_record(item) for item in accepted]
        snapshot_id = hashlib.sha256(
            json.dumps(
                snapshot_payload, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()[:16]
        self._snapshot = _Snapshot(snapshot_id=snapshot_id, skills=tuple(accepted))
        return SkillRefreshResponse(
            snapshot_id=snapshot_id,
            skill_count=len(accepted),
        )

    def list_skills(
        self, limit: int | None = None, cursor: str | None = None
    ) -> SkillListResponse:
        bounded = self._limit(
            limit,
            self.config.limits.list_default_limit,
            self.config.limits.list_max_limit,
        )
        start = 0 if cursor is None else self._cursor_offset(cursor)
        entries = self._active()
        page = entries[start : start + bounded]
        next_cursor = (
            f"{self.snapshot_id}:{start + bounded}"
            if start + bounded < len(entries)
            else None
        )
        return SkillListResponse(
            skills=tuple(self._card(item) for item in page),
            skill_count=len(entries),
            next_cursor=next_cursor,
            snapshot_id=self.snapshot_id,
        )

    def search_skills(
        self, query: str, limit: int | None = None
    ) -> SkillSearchResponse:
        terms = _SEARCH_TERM.findall(query.casefold()) if isinstance(query, str) else []
        if not terms:
            raise SkillsError(
                "SKILLS_QUERY_INVALID", "Search query must contain at least one word"
            )
        ranked: list[tuple[int, str, _SkillEntry]] = []
        for entry in self._active():
            haystack = " ".join(
                (
                    entry.id,
                    entry.summary,
                    entry.category,
                    " ".join(entry.capabilities),
                    entry.status,
                )
            ).casefold()
            matched = sum(1 for term in terms if term in haystack)
            if matched:
                ranked.append((-matched, entry.id, entry))
        ranked.sort(key=lambda item: (item[0], item[1]))
        bounded = self._limit(
            limit,
            self.config.limits.search_default_limit,
            self.config.limits.search_max_limit,
        )
        return SkillSearchResponse(
            skills=tuple(self._card(item[2]) for item in ranked[:bounded]),
            snapshot_id=self.snapshot_id,
        )

    def load_skill(self, skill_id: str) -> SkillLoadResponse:
        entry = self._entry(skill_id)
        return SkillLoadResponse(
            skill=self._card(entry),
            content=entry.content,
            sha256=entry.content_hash,
            file_count=len(entry.files),
            reference_group_counts=dict(entry.reference_group_counts),
            snapshot_id=self.snapshot_id,
        )

    def search_skill_files(
        self, skill_id: str, query: str, limit: int | None = None
    ) -> SkillFileSearchResponse:
        terms = _SEARCH_TERM.findall(query.casefold()) if isinstance(query, str) else []
        if not terms:
            raise SkillsError(
                "SKILLS_QUERY_INVALID",
                "File search query must contain at least one word",
            )
        entry = self._entry(skill_id)
        bounded = self._limit(
            limit,
            self.config.limits.file_search_default_limit,
            self.config.limits.file_search_max_limit,
        )
        matches = tuple(
            SkillFileMatch(path=item.path, group=item.group)
            for item in entry.files
            if all(term in item.path.casefold() for term in terms)
        )[:bounded]
        return SkillFileSearchResponse(
            skill_id=entry.id,
            files=matches,
            snapshot_id=self.snapshot_id,
        )

    def read_skill_file(self, skill_id: str, relative_path: str) -> SkillFileResponse:
        entry = self._entry(skill_id)
        path = self._safe_relative_path(relative_path).as_posix()
        for item in entry.files:
            if item.path == path:
                return SkillFileResponse(
                    skill_id=entry.id,
                    path=item.path,
                    size=item.size,
                    sha256=item.sha256,
                    content=item.content,
                    snapshot_id=self.snapshot_id,
                )
        raise SkillsError(
            "SKILLS_FILE_UNKNOWN", "Skill file is not in the active snapshot", subject=path
        )

    def evaluate_skill(self, skill_id: str) -> SkillEvaluationResponse:
        entry = self._entry(skill_id)
        return SkillEvaluationResponse(
            skill_id=entry.id,
            snapshot_id=self.snapshot_id,
            evidence=SkillEvaluationEvidence(
                file_count=len(entry.files),
                total_bytes=sum(item.size for item in entry.files),
                reference_group_counts=dict(entry.reference_group_counts),
                entrypoint_sha256=entry.content_hash,
                supported_file_count=len(entry.files),
            ),
        )

    def validate_create(self, skill_id: str, skill_md: str) -> ProposedSkillCreate:
        self._validate_skill_id(skill_id)
        if not isinstance(skill_md, str):
            raise SkillsError(
                "SKILLS_CONTENT_INVALID", "Skill content must be UTF-8 text"
            )
        if any(entry.id == skill_id for entry in self._active()) or (
            self.root / skill_id
        ).exists():
            raise SkillsError(
                "SKILLS_ALREADY_EXISTS", "Skill already exists", subject=skill_id
            )
        proposed = self._entry_from_files(
            source_directory=skill_id,
            files=(self._virtual_file("SKILL.md", skill_md),),
        )
        if proposed.id != skill_id:
            raise SkillsError(
                "SKILLS_ID_MISMATCH",
                "Requested skill ID does not match SKILL.md frontmatter name",
                subject=skill_id,
            )
        return ProposedSkillCreate(
            skill_id=skill_id,
            content=skill_md,
            after_sha256=hashlib.sha256(skill_md.encode("utf-8")).hexdigest(),
        )

    def validate_replacement(
        self, skill_id: str, relative_path: str, content: str
    ) -> ProposedSkillReplacement:
        entry = self._entry(skill_id)
        path = self._safe_relative_path(relative_path).as_posix()
        if not isinstance(content, str):
            raise SkillsError(
                "SKILLS_CONTENT_INVALID", "Replacement content must be UTF-8 text"
            )
        current = next((item for item in entry.files if item.path == path), None)
        if current is None:
            raise SkillsError(
                "SKILLS_FILE_UNKNOWN", "Skill file is not in the active snapshot", subject=path
            )
        if current.content is None:
            raise SkillsError(
                "SKILLS_CONTENT_INVALID", "Binary skill files cannot be improved as text"
            )
        replacement = self._virtual_file(path, content)
        proposed_files = tuple(
            replacement if item.path == path else item for item in entry.files
        )
        proposed = self._entry_from_files(
            source_directory=entry.source_directory,
            files=proposed_files,
        )
        if proposed.id != entry.id:
            raise SkillsError(
                "SKILLS_ID_MISMATCH",
                "Replacement changes the canonical skill ID",
                subject=skill_id,
            )
        return ProposedSkillReplacement(
            skill_id=entry.id,
            relative_path=path,
            target_path=self.root
            / entry.source_directory
            / Path(*PurePosixPath(path).parts),
            current_content=current.content,
            content=content,
            before_sha256=current.sha256,
            after_sha256=replacement.sha256,
        )

    def _build_entry(self, skill_root: Path) -> _SkillEntry:
        files: list[_FileEntry] = []
        total = 0
        for current_root, directory_names, file_names in os.walk(
            skill_root, topdown=True, followlinks=False
        ):
            current = Path(current_root)
            self._assert_safe_chain(skill_root, current)
            directory_names.sort(key=str.casefold)
            file_names.sort(key=str.casefold)
            for directory_name in directory_names:
                self._assert_safe_chain(skill_root, current / directory_name)
            for file_name in file_names:
                path = current / file_name
                self._assert_safe_chain(skill_root, path)
                relative = path.relative_to(skill_root).as_posix()
                item = self._read_file(skill_root, relative)
                total += item.size
                if total > self.config.limits.max_skill_bytes:
                    raise SkillsError(
                        "SKILLS_SIZE_EXCEEDED", "Skill exceeds maximum total size"
                    )
                files.append(item)
        return self._entry_from_files(
            source_directory=skill_root.name,
            files=tuple(files),
        )

    def _entry_from_files(
        self, *, source_directory: str, files: tuple[_FileEntry, ...]
    ) -> _SkillEntry:
        if not files:
            raise SkillsError("SKILLS_ENTRYPOINT_MISSING", "SKILL.md is required")
        total = sum(item.size for item in files)
        if total > self.config.limits.max_skill_bytes:
            raise SkillsError(
                "SKILLS_SIZE_EXCEEDED", "Skill exceeds maximum total size"
            )
        entrypoint = next((item for item in files if item.path == "SKILL.md"), None)
        if entrypoint is None or entrypoint.content is None:
            raise SkillsError("SKILLS_ENTRYPOINT_MISSING", "SKILL.md is required")
        frontmatter = self._frontmatter(entrypoint.content)
        name = frontmatter.get("name")
        description = frontmatter.get("description")
        if not isinstance(name, str) or not name.strip():
            raise SkillsError(
                "SKILLS_FRONTMATTER_INVALID", "SKILL.md name is required"
            )
        if not isinstance(description, str) or not description.strip():
            raise SkillsError(
                "SKILLS_FRONTMATTER_INVALID", "SKILL.md description is required"
            )
        canonical_id = name.strip()
        self._validate_skill_id(canonical_id)
        category = frontmatter.get("category", "uncategorized")
        status = frontmatter.get("status", "active")
        capabilities = frontmatter.get("capabilities", ())
        if not isinstance(category, str) or not category.strip():
            raise SkillsError(
                "SKILLS_FRONTMATTER_INVALID", "Skill category must be text"
            )
        if not isinstance(status, str) or not status.strip():
            raise SkillsError(
                "SKILLS_FRONTMATTER_INVALID", "Skill status must be text"
            )
        if isinstance(capabilities, list):
            capabilities = tuple(capabilities)
        if not isinstance(capabilities, tuple) or not all(
            isinstance(item, str) and item.strip() for item in capabilities
        ):
            raise SkillsError(
                "SKILLS_FRONTMATTER_INVALID",
                "Skill capabilities must be a string list",
            )
        groups: dict[str, int] = {}
        for item in files:
            groups[item.group] = groups.get(item.group, 0) + 1
        ordered_files = tuple(sorted(files, key=lambda item: item.path))
        return _SkillEntry(
            id=canonical_id,
            source_directory=source_directory,
            summary=description.strip(),
            category=category.strip(),
            capabilities=tuple(item.strip() for item in capabilities),
            status=status.strip(),
            content=entrypoint.content,
            content_hash=entrypoint.sha256,
            files=ordered_files,
            reference_group_counts=MappingProxyType(dict(sorted(groups.items()))),
        )

    def _read_file(self, root: Path, relative_path: str) -> _FileEntry:
        relative = self._safe_relative_path(relative_path)
        candidate = root.joinpath(*relative.parts)
        self._assert_safe_chain(root, candidate)
        if not candidate.is_file():
            raise SkillsError("SKILLS_FILE_INVALID", "Skill entry must be a file")
        suffix = candidate.suffix.casefold()
        if suffix not in self.config.validation.allowed_suffixes:
            raise SkillsError(
                "SKILLS_SUFFIX_FORBIDDEN",
                f"Skill file suffix is not configured: {suffix or '<none>'}",
            )
        data = candidate.read_bytes()
        if len(data) > self.config.limits.max_file_bytes:
            raise SkillsError(
                "SKILLS_SIZE_EXCEEDED", "Skill file exceeds maximum size"
            )
        content: str | None
        if suffix == ".png":
            content = None
        else:
            try:
                content = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise SkillsError(
                    "SKILLS_ENCODING_INVALID", "Skill file must be UTF-8 text"
                ) from exc
        path = relative.as_posix()
        return _FileEntry(
            path=path,
            group=path.split("/", 1)[0] if "/" in path else "root",
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            content=content,
        )

    def _virtual_file(self, relative_path: str, content: str) -> _FileEntry:
        relative = self._safe_relative_path(relative_path)
        suffix = relative.suffix.casefold()
        if suffix not in self.config.validation.allowed_suffixes or suffix == ".png":
            raise SkillsError(
                "SKILLS_SUFFIX_FORBIDDEN", "Replacement target must be configured text"
            )
        encoded = content.encode("utf-8")
        if len(encoded) > self.config.limits.max_file_bytes:
            raise SkillsError(
                "SKILLS_SIZE_EXCEEDED", "Skill file exceeds maximum size"
            )
        path = relative.as_posix()
        return _FileEntry(
            path=path,
            group=path.split("/", 1)[0] if "/" in path else "root",
            size=len(encoded),
            sha256=hashlib.sha256(encoded).hexdigest(),
            content=content,
        )

    def _entry(self, skill_id: str) -> _SkillEntry:
        self._validate_skill_id(skill_id)
        for entry in self._active():
            if entry.id == skill_id:
                return entry
        raise SkillsError(
            "SKILLS_UNKNOWN", "Skill is not in the active snapshot", subject=skill_id
        )

    def _active(self) -> tuple[_SkillEntry, ...]:
        if self._snapshot is None:
            raise SkillsError("SKILLS_SNAPSHOT_MISSING", "No active Skills snapshot")
        return self._snapshot.skills

    def _cursor_offset(self, cursor: str) -> int:
        if not isinstance(cursor, str) or ":" not in cursor:
            raise SkillsError(
                "SKILLS_CURSOR_INVALID", "Cursor was not issued by list_skills"
            )
        snapshot_id, raw_offset = cursor.rsplit(":", 1)
        if (
            snapshot_id != self.snapshot_id
            or not raw_offset.isdecimal()
            or int(raw_offset) > self.skill_count
        ):
            raise SkillsError(
                "SKILLS_CURSOR_INVALID", "Cursor is stale or outside the active snapshot"
            )
        return int(raw_offset)

    def _safe_relative_path(self, value: str) -> PurePosixPath:
        if (
            not isinstance(value, str)
            or not value
            or "\x00" in value
            or (self.config.validation.reject_backslashes and "\\" in value)
        ):
            raise SkillsError(
                "SKILLS_PATH_UNSAFE", "Skill file path is empty or unsafe"
            )
        path = PurePosixPath(value)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise SkillsError(
                "SKILLS_PATH_UNSAFE", "Skill file path must remain relative"
            )
        return path

    def _assert_safe_chain(self, root: Path, candidate: Path) -> None:
        try:
            relative = candidate.relative_to(root)
        except ValueError as exc:
            raise SkillsError(
                "SKILLS_PATH_UNSAFE", "Path is outside the selected skill"
            ) from exc
        current = root
        self._assert_no_link(current)
        for part in relative.parts:
            current = current / part
            self._assert_no_link(current)

    def _assert_no_link(self, path: Path) -> None:
        try:
            info = os.lstat(path)
        except FileNotFoundError as exc:
            raise SkillsError("SKILLS_PATH_MISSING", "Skill path does not exist") from exc
        if self.config.validation.reject_links and stat.S_ISLNK(info.st_mode):
            raise SkillsError("SKILLS_LINK_REJECTED", "Symbolic links are not allowed")
        attributes = getattr(info, "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        if self.config.validation.reject_reparse_points and attributes & reparse_flag:
            raise SkillsError("SKILLS_LINK_REJECTED", "Reparse points are not allowed")
        if (
            self.config.validation.reject_hard_links
            and stat.S_ISREG(info.st_mode)
            and info.st_nlink > 1
        ):
            raise SkillsError("SKILLS_LINK_REJECTED", "Hard-linked files are not allowed")

    def _validate_skill_id(self, skill_id: str) -> None:
        if (
            not isinstance(skill_id, str)
            or self.config.validation.skill_id_pattern.fullmatch(skill_id) is None
        ):
            raise SkillsError(
                "SKILLS_ID_INVALID", "Skill ID must be lowercase and hyphenated"
            )

    @staticmethod
    def _frontmatter(content: str) -> dict[str, Any]:
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            raise SkillsError(
                "SKILLS_FRONTMATTER_INVALID",
                "SKILL.md must begin with YAML frontmatter",
            )
        closing = next(
            (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
            None,
        )
        if closing is None:
            raise SkillsError(
                "SKILLS_FRONTMATTER_INVALID", "SKILL.md frontmatter is not closed"
            )
        payload: dict[str, Any] = {}
        raw = lines[1:closing]
        index = 0
        while index < len(raw):
            line = raw[index]
            if not line.strip() or line.lstrip().startswith("#"):
                index += 1
                continue
            if line[:1].isspace():
                raise SkillsError(
                    "SKILLS_FRONTMATTER_INVALID", "Unexpected frontmatter indentation"
                )
            match = _FRONTMATTER_KEY.fullmatch(line)
            if match is None:
                raise SkillsError(
                    "SKILLS_FRONTMATTER_INVALID", "Frontmatter entry is invalid"
                )
            key, value = match.group(1), (match.group(2) or "")
            index += 1
            if value in {"|", ">"}:
                continuation: list[str] = []
                while index < len(raw) and (
                    raw[index].startswith(" ") or not raw[index].strip()
                ):
                    continuation.append(raw[index].lstrip())
                    index += 1
                payload[key] = (
                    "\n".join(continuation).strip()
                    if value == "|"
                    else " ".join(item.strip() for item in continuation).strip()
                )
                continue
            if value == "":
                items: list[str] = []
                while index < len(raw) and raw[index].startswith("  - "):
                    items.append(SkillCatalogue._scalar(raw[index][4:].strip()))
                    index += 1
                payload[key] = items if items else ""
                continue
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                payload[key] = (
                    [SkillCatalogue._scalar(item.strip()) for item in inner.split(",")]
                    if inner
                    else []
                )
            else:
                payload[key] = SkillCatalogue._scalar(value.strip())
        return payload

    @staticmethod
    def _scalar(value: str) -> str:
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            try:
                parsed = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                return value[1:-1]
            return str(parsed)
        return value

    @staticmethod
    def _card(entry: _SkillEntry) -> SkillCard:
        return SkillCard(
            id=entry.id,
            summary=entry.summary,
            category=entry.category,
            capabilities=entry.capabilities,
            status=entry.status,
        )

    @staticmethod
    def _fingerprint_record(entry: _SkillEntry) -> dict[str, Any]:
        return {
            "id": entry.id,
            "source_directory": entry.source_directory,
            "summary": entry.summary,
            "category": entry.category,
            "capabilities": list(entry.capabilities),
            "status": entry.status,
            "files": [
                {"path": item.path, "size": item.size, "sha256": item.sha256}
                for item in entry.files
            ],
        }

    @staticmethod
    def _limit(value: int | None, default: int, maximum: int) -> int:
        limit = default if value is None else value
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= maximum:
            raise SkillsError(
                "SKILLS_LIMIT_INVALID", f"Limit must be between 1 and {maximum}"
            )
        return limit
