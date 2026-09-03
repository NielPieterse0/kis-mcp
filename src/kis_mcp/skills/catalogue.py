from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..capabilities.settings import load_capability_settings
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
from .metadata import enrich_skill_card
from .source import SkillSource, SkillSourceReader


_SEARCH_TERM = re.compile(r"[a-z0-9-]+")


@dataclass(frozen=True, slots=True)
class _Snapshot:
    snapshot_id: str
    skills: tuple[SkillSource, ...]


@dataclass(frozen=True, slots=True)
class SkillRefreshDiagnostic:
    source_directory: str
    code: str
    message: str


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
    """Immutable snapshot and query service for validated skill sources."""

    def __init__(self, config: SkillsConfig) -> None:
        self.config = config
        self.capability_settings = load_capability_settings()
        self.source_reader = SkillSourceReader(config)
        self.root = self.source_reader.root
        self._snapshot: _Snapshot | None = None
        self._diagnostics: tuple[SkillRefreshDiagnostic, ...] = ()
        self.refresh_skills()

    @property
    def snapshot_id(self) -> str:
        if self._snapshot is None:
            raise SkillsError("SKILLS_SNAPSHOT_MISSING", "No active Skills snapshot")
        return self._snapshot.snapshot_id

    @property
    def skill_count(self) -> int:
        return len(self._active())

    @property
    def diagnostics(self) -> tuple[SkillRefreshDiagnostic, ...]:
        return self._diagnostics

    def refresh_skills(self) -> SkillRefreshResponse:
        accepted: list[SkillSource] = []
        diagnostics: list[SkillRefreshDiagnostic] = []
        canonical_sources: dict[str, str] = {}
        try:
            paths = sorted(self.root.iterdir(), key=lambda item: item.name.casefold())
        except OSError as exc:
            paths = []
            diagnostics.append(
                SkillRefreshDiagnostic(
                    source_directory=".",
                    code="SKILLS_ROOT_UNAVAILABLE",
                    message=str(exc),
                )
            )
        for path in paths:
            if path.name.startswith("."):
                continue
            try:
                self.source_reader.assert_no_link(path)
                if not path.is_dir():
                    raise SkillsError(
                        "SKILLS_SOURCE_INVALID", "Skill source must be a directory"
                    )
                entry = self.source_reader.read_directory(path)
                previous = canonical_sources.get(entry.id)
                if previous is not None:
                    raise SkillsError(
                        "SKILLS_ID_DUPLICATE",
                        f"Canonical skill ID duplicates source {previous}",
                    )
                canonical_sources[entry.id] = path.name
                accepted.append(entry)
            except SkillsError as exc:
                diagnostics.append(
                    SkillRefreshDiagnostic(
                        source_directory=path.name,
                        code=exc.code,
                        message=exc.message,
                    )
                )
            except OSError as exc:
                diagnostics.append(
                    SkillRefreshDiagnostic(
                        source_directory=path.name,
                        code="SKILLS_SOURCE_UNREADABLE",
                        message=str(exc),
                    )
                )

        present_ids = {entry.id for entry in accepted}
        for skill_id in self.config.required_skills:
            if skill_id not in present_ids:
                diagnostics.append(
                    SkillRefreshDiagnostic(
                        source_directory=skill_id,
                        code="SKILLS_REQUIRED_MISSING",
                        message="Configured required skill is missing or invalid",
                    )
                )

        accepted.sort(key=lambda item: item.id)
        snapshot_id = hashlib.sha256(
            json.dumps(
                [self._fingerprint_record(item) for item in accepted],
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:16]
        self._snapshot = _Snapshot(snapshot_id=snapshot_id, skills=tuple(accepted))
        self._diagnostics = tuple(diagnostics)
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
        ranked: list[tuple[int, str, SkillSource]] = []
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
        path = self.source_reader.safe_relative_path(relative_path).as_posix()
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

    def read_skill_resource_bytes(self, skill_id: str, relative_path: str) -> bytes:
        """Return bytes only when they still match the active validated snapshot."""
        entry = self._entry(skill_id)
        path = self.source_reader.safe_relative_path(relative_path).as_posix()
        item = next((candidate for candidate in entry.files if candidate.path == path), None)
        if item is None:
            raise SkillsError(
                "SKILLS_FILE_UNKNOWN", "Skill file is not in the active snapshot", subject=path
            )
        skill_root = self.root / entry.source_directory
        target = self.source_reader.target_path(entry.source_directory, path)
        try:
            self.source_reader.assert_safe_chain(skill_root, target)
            data = target.read_bytes()
            self.source_reader.assert_safe_chain(skill_root, target)
        except SkillsError as exc:
            if exc.code in {"SKILLS_LINK_REJECTED", "SKILLS_PATH_UNSAFE"}:
                raise
            raise SkillsError(
                "SKILLS_RESOURCE_STALE",
                "Skill resource no longer matches the active snapshot",
                subject=path,
            ) from exc
        except OSError as exc:
            raise SkillsError(
                "SKILLS_RESOURCE_STALE",
                "Skill resource no longer matches the active snapshot",
                subject=path,
            ) from exc
        if len(data) != item.size or hashlib.sha256(data).hexdigest() != item.sha256:
            raise SkillsError(
                "SKILLS_RESOURCE_STALE",
                "Skill resource no longer matches the active snapshot",
                subject=path,
            )
        return data

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
        self.source_reader.validate_skill_id(skill_id)
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
        proposed = self.source_reader.build_source(
            source_directory=skill_id,
            files=(self.source_reader.virtual_file("SKILL.md", skill_md),),
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
        path = self.source_reader.safe_relative_path(relative_path).as_posix()
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
        replacement = self.source_reader.virtual_file(path, content)
        proposed = self.source_reader.build_source(
            source_directory=entry.source_directory,
            files=tuple(replacement if item.path == path else item for item in entry.files),
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
            target_path=self.source_reader.target_path(entry.source_directory, path),
            current_content=current.content,
            content=content,
            before_sha256=current.sha256,
            after_sha256=replacement.sha256,
        )

    def _entry(self, skill_id: str) -> SkillSource:
        self.source_reader.validate_skill_id(skill_id)
        for entry in self._active():
            if entry.id == skill_id:
                return entry
        raise SkillsError(
            "SKILLS_UNKNOWN", "Skill is not in the active snapshot", subject=skill_id
        )

    def _active(self) -> tuple[SkillSource, ...]:
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

    def _card(self, entry: SkillSource) -> SkillCard:
        return enrich_skill_card(
            SkillCard(
                id=entry.id,
                summary=entry.summary,
                category=entry.category,
                capabilities=entry.capabilities,
                status=entry.status,
            ),
            self.capability_settings,
        )

    def _fingerprint_record(self, entry: SkillSource) -> dict[str, Any]:
        card = self._card(entry)
        return {
            "id": entry.id,
            "source_directory": entry.source_directory,
            "summary": card.summary,
            "category": card.category,
            "capabilities": list(card.capabilities),
            "status": card.status,
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
