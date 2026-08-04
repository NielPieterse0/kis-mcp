from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


APPROVED_SKILLS_ROOT = r"C:\Projects\.agents\skills"
APPROVED_SKILLS_STAGING_ROOT = r"C:\Projects\.kis-mcp\temp\skills"


@dataclass(frozen=True, slots=True)
class SkillsLimits:
    max_file_bytes: int
    max_skill_bytes: int
    list_default_limit: int
    list_max_limit: int
    search_default_limit: int
    search_max_limit: int
    file_search_default_limit: int
    file_search_max_limit: int


@dataclass(frozen=True, slots=True)
class SkillsValidation:
    skill_id_pattern: re.Pattern[str]
    allowed_suffixes: tuple[str, ...]
    reject_links: bool
    reject_reparse_points: bool
    reject_hard_links: bool
    reject_backslashes: bool


@dataclass(frozen=True, slots=True)
class SkillsConfig:
    root: Path
    staging_root: Path
    limits: SkillsLimits
    validation: SkillsValidation


_ROOT_KEYS = {"schema_version", "root", "staging_root", "limits", "validation"}
_LIMIT_KEYS = {
    "max_file_bytes",
    "max_skill_bytes",
    "list_default_limit",
    "list_max_limit",
    "search_default_limit",
    "search_max_limit",
    "file_search_default_limit",
    "file_search_max_limit",
}
_VALIDATION_KEYS = {
    "skill_id_pattern",
    "allowed_suffixes",
    "reject_links",
    "reject_reparse_points",
    "reject_hard_links",
    "reject_backslashes",
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required Skills settings are missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in Skills settings: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Skills settings root must be an object")
    return value


def _closed_object(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be an object")
    actual = set(value)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing:
        raise RuntimeError(f"{label} is missing keys: {', '.join(missing)}")
    if unexpected:
        raise RuntimeError(f"{label} contains unexpected keys: {', '.join(unexpected)}")
    return value


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise RuntimeError(f"Skills limits value {label} must be a positive integer")
    return value


def _true(value: Any, label: str) -> bool:
    if value is not True:
        raise RuntimeError(f"Skills validation value {label} must be true")
    return True


def _same_windows_path(left: str, right: str) -> bool:
    return str(Path(left)).rstrip("\\/").casefold() == str(Path(right)).rstrip("\\/").casefold()


def load_skills_config(repository_root: Path | None = None) -> SkillsConfig:
    root = (repository_root or Path(__file__).resolve().parents[3]).resolve()
    raw = _closed_object(
        _read_json(root / "settings" / "skills.settings.json"),
        _ROOT_KEYS,
        "Skills settings",
    )
    if raw["schema_version"] != 1:
        raise RuntimeError("Skills settings schema_version must be 1")

    skills_root = str(raw["root"])
    staging_root = str(raw["staging_root"])
    if not _same_windows_path(skills_root, APPROVED_SKILLS_ROOT):
        raise RuntimeError(f"The approved Skills root is fixed at {APPROVED_SKILLS_ROOT}")
    if not _same_windows_path(staging_root, APPROVED_SKILLS_STAGING_ROOT):
        raise RuntimeError(
            f"The approved Skills staging root is fixed at {APPROVED_SKILLS_STAGING_ROOT}"
        )

    limits_raw = _closed_object(raw["limits"], _LIMIT_KEYS, "Skills limits")
    limits = SkillsLimits(
        **{key: _positive_int(limits_raw[key], key) for key in _LIMIT_KEYS}
    )
    if (
        limits.max_skill_bytes < limits.max_file_bytes
        or limits.list_default_limit > limits.list_max_limit
        or limits.search_default_limit > limits.search_max_limit
        or limits.file_search_default_limit > limits.file_search_max_limit
    ):
        raise RuntimeError("Skills limits are internally inconsistent")

    validation_raw = _closed_object(
        raw["validation"], _VALIDATION_KEYS, "Skills validation"
    )
    pattern_value = validation_raw["skill_id_pattern"]
    if not isinstance(pattern_value, str) or not pattern_value:
        raise RuntimeError("Skills validation skill_id_pattern must be a string")
    try:
        pattern = re.compile(pattern_value)
    except re.error as exc:
        raise RuntimeError("Skills validation skill_id_pattern is invalid") from exc

    suffixes_value = validation_raw["allowed_suffixes"]
    if (
        not isinstance(suffixes_value, list)
        or not suffixes_value
        or not all(
            isinstance(item, str)
            and re.fullmatch(r"\.[a-z0-9]+", item) is not None
            for item in suffixes_value
        )
        or len(set(suffixes_value)) != len(suffixes_value)
    ):
        raise RuntimeError("Skills validation allowed_suffixes is invalid")

    validation = SkillsValidation(
        skill_id_pattern=pattern,
        allowed_suffixes=tuple(suffixes_value),
        reject_links=_true(validation_raw["reject_links"], "reject_links"),
        reject_reparse_points=_true(
            validation_raw["reject_reparse_points"], "reject_reparse_points"
        ),
        reject_hard_links=_true(
            validation_raw["reject_hard_links"], "reject_hard_links"
        ),
        reject_backslashes=_true(
            validation_raw["reject_backslashes"], "reject_backslashes"
        ),
    )
    return SkillsConfig(
        root=Path(skills_root),
        staging_root=Path(staging_root),
        limits=limits,
        validation=validation,
    )
