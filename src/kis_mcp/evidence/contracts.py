from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping


class EvidenceWriteDisposition(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    CONFLICT = "conflict"
    NOT_WRITTEN = "not_written"


class EvidenceError(RuntimeError):
    pass


class EvidenceConflictError(EvidenceError):
    pass


class EvidenceCorruptionError(EvidenceError):
    pass


@dataclass(frozen=True, slots=True)
class FileWriteResult:
    path: str
    disposition: EvidenceWriteDisposition
    sha256: str
    previous_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class GenerationWriteResult:
    generation_id: str
    disposition: EvidenceWriteDisposition
    previous_generation_id: str | None
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class EvidenceGeneration:
    generation_id: str
    metadata: Mapping[str, Any]
    artifacts: Mapping[str, bytes]
    manifest_sha256: str


__all__ = [
    "EvidenceConflictError",
    "EvidenceCorruptionError",
    "EvidenceError",
    "EvidenceGeneration",
    "EvidenceWriteDisposition",
    "FileWriteResult",
    "GenerationWriteResult",
]
