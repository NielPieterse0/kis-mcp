from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


PUBLIC_SKILLS_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class SkillCard:
    id: str
    summary: str
    category: str
    capabilities: tuple[str, ...]
    status: str
    schema_version: int = PUBLIC_SKILLS_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class SkillListResponse:
    skills: tuple[SkillCard, ...]
    skill_count: int
    next_cursor: str | None
    snapshot_id: str
    schema_version: int = PUBLIC_SKILLS_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class SkillSearchResponse:
    skills: tuple[SkillCard, ...]
    snapshot_id: str
    schema_version: int = PUBLIC_SKILLS_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class SkillLoadResponse:
    skill: SkillCard
    content: str
    sha256: str
    file_count: int
    reference_group_counts: Mapping[str, int]
    snapshot_id: str
    schema_version: int = PUBLIC_SKILLS_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class SkillFileMatch:
    path: str
    group: str
    schema_version: int = PUBLIC_SKILLS_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class SkillFileSearchResponse:
    skill_id: str
    files: tuple[SkillFileMatch, ...]
    snapshot_id: str
    schema_version: int = PUBLIC_SKILLS_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class SkillFileResponse:
    skill_id: str
    path: str
    size: int
    sha256: str
    content: str | None
    snapshot_id: str
    schema_version: int = PUBLIC_SKILLS_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class SkillRefreshResponse:
    snapshot_id: str
    skill_count: int
    schema_version: int = PUBLIC_SKILLS_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class SkillEvaluationEvidence:
    file_count: int
    total_bytes: int
    reference_group_counts: Mapping[str, int]
    entrypoint_sha256: str
    supported_file_count: int
    schema_version: int = PUBLIC_SKILLS_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class SkillEvaluationResponse:
    skill_id: str
    snapshot_id: str
    evidence: SkillEvaluationEvidence
    schema_version: int = PUBLIC_SKILLS_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class SkillMutationResponse:
    skill_id: str
    relative_path: str | None
    before_sha256: str | None
    after_sha256: str
    snapshot_id: str
    changed_state: bool = True
    schema_version: int = PUBLIC_SKILLS_SCHEMA_VERSION
