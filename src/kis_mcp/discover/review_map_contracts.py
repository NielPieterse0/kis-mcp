from __future__ import annotations

from dataclasses import dataclass

REVIEW_MAP_SCHEMA_VERSION = 1
REVIEW_MAP_TOOL = "build_review_map"


def _positive(value: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class ReviewMapLimits:
    max_files: int = 200
    max_sections: int = 40
    max_relationships: int = 100

    def __post_init__(self) -> None:
        _positive(self.max_files, "max_files")
        _positive(self.max_sections, "max_sections")
        _positive(self.max_relationships, "max_relationships")
