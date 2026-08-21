from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ROOT_KEYS = frozenset(
    {
        "schema_version",
        "enabled",
        "host_instance",
        "state_namespace",
        "receipt_retention",
        "freshness_stale_after_seconds",
        "poll_interval_seconds",
        "initial_delay_seconds",
        "overlap_seconds",
        "max_candidates",
        "max_external_reads",
        "max_mutations",
        "ambiguous_risk_triggers",
        "targets",
        "surfaces",
    }
)
_TARGET_KEYS = frozenset({"project_id", "repository", "default_branch"})
_SURFACE_KEYS = frozenset(
    {
        "id",
        "path_patterns",
        "risk_triggers",
        "runtime_instance",
        "refresh_rule",
        "verification_procedure",
        "expected_invariant",
        "evidence_target",
        "terminal_success_criterion",
    }
)
_NAMESPACE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_PROJECT_ID = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")
_SURFACE_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_REFRESH_RULES = frozenset({"none", "refresh", "restart"})


class PostMergeCommissioningSettingsError(RuntimeError):
    pass


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    actual = {str(key) for key in value}
    unknown = sorted(actual - expected)
    missing = sorted(expected - actual)
    if unknown:
        raise PostMergeCommissioningSettingsError(f"{label} has unknown keys: {unknown}")
    if missing:
        raise PostMergeCommissioningSettingsError(f"{label} is missing required keys: {missing}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PostMergeCommissioningSettingsError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PostMergeCommissioningSettingsError(f"{label} must be an integer")
    if not minimum <= value <= maximum:
        raise PostMergeCommissioningSettingsError(
            f"{label} must be between {minimum} and {maximum}"
        )
    return value


def _string_array(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise PostMergeCommissioningSettingsError(f"{label} must be an array")
    result = tuple(_text(item, f"{label}[]") for item in value)
    if len(set(result)) != len(result):
        raise PostMergeCommissioningSettingsError(f"{label} contains duplicate values")
    return result


def _risk_trigger_catalogue() -> frozenset[str]:
    path = Path(__file__).resolve().parents[3] / "settings" / "change-governance.settings.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    values = document.get("risk_triggers")
    if not isinstance(values, Mapping):
        raise PostMergeCommissioningSettingsError(
            "change-governance risk_triggers must be an object"
        )
    return frozenset(str(key) for key in values)


def _validate_risks(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    unknown = sorted(set(values) - _risk_trigger_catalogue())
    if unknown:
        raise PostMergeCommissioningSettingsError(f"{label} has unknown risk triggers: {unknown}")
    return tuple(sorted(values))


def _path_pattern(value: Any, label: str) -> str:
    pattern = _text(value, label)
    if "\\" in pattern or pattern.startswith("/") or ":" in pattern:
        raise PostMergeCommissioningSettingsError(f"{label} must be a repository-relative glob")
    parts = tuple(part for part in pattern.split("/") if part)
    if not parts or any(part in {".", ".."} for part in parts):
        raise PostMergeCommissioningSettingsError(f"{label} must be a repository-relative glob")
    return pattern


@dataclass(frozen=True, slots=True)
class PostMergeTargetSettings:
    project_id: str
    repository: str
    default_branch: str

    def __post_init__(self) -> None:
        project_id = _text(self.project_id, "project_id")
        if _PROJECT_ID.fullmatch(project_id) is None:
            raise PostMergeCommissioningSettingsError("project_id must use lower-case kebab-case")
        repository = _text(self.repository, "repository")
        if _REPOSITORY.fullmatch(repository) is None:
            raise PostMergeCommissioningSettingsError("repository must be owner/name")
        branch = _text(self.default_branch, "default_branch")
        if _BRANCH.fullmatch(branch) is None or ".." in branch or branch.startswith("/"):
            raise PostMergeCommissioningSettingsError("default_branch is invalid")
        object.__setattr__(self, "project_id", project_id)
        object.__setattr__(self, "repository", repository)
        object.__setattr__(self, "default_branch", branch)


@dataclass(frozen=True, slots=True)
class CommissioningSurfaceSettings:
    id: str
    path_patterns: tuple[str, ...]
    risk_triggers: tuple[str, ...]
    runtime_instance: str
    refresh_rule: str
    verification_procedure: str
    expected_invariant: str
    evidence_target: str
    terminal_success_criterion: str

    def __post_init__(self) -> None:
        surface_id = _text(self.id, "surface.id")
        if _SURFACE_ID.fullmatch(surface_id) is None:
            raise PostMergeCommissioningSettingsError("surface.id must be lower-case kebab-case")
        if not self.path_patterns and not self.risk_triggers:
            raise PostMergeCommissioningSettingsError(
                f"surface {surface_id} requires path_patterns or risk_triggers"
            )
        refresh_rule = _text(self.refresh_rule, f"surface {surface_id}.refresh_rule")
        if refresh_rule not in _REFRESH_RULES:
            raise PostMergeCommissioningSettingsError(
                f"surface {surface_id}.refresh_rule is invalid"
            )
        object.__setattr__(self, "id", surface_id)
        object.__setattr__(self, "path_patterns", tuple(sorted(self.path_patterns)))
        object.__setattr__(self, "risk_triggers", tuple(sorted(self.risk_triggers)))
        object.__setattr__(self, "refresh_rule", refresh_rule)


@dataclass(frozen=True, slots=True)
class PostMergeCommissioningSettings:
    enabled: bool
    host_instance: str
    state_namespace: str
    receipt_retention: int
    freshness_stale_after_seconds: int
    poll_interval_seconds: int
    initial_delay_seconds: int
    overlap_seconds: int
    max_candidates: int
    max_external_reads: int
    max_mutations: int
    ambiguous_risk_triggers: tuple[str, ...]
    targets: tuple[PostMergeTargetSettings, ...]
    surfaces: tuple[CommissioningSurfaceSettings, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise PostMergeCommissioningSettingsError("schema_version must be 1")
        if not isinstance(self.enabled, bool):
            raise PostMergeCommissioningSettingsError("enabled must be a boolean")
        if self.host_instance != "kis-op":
            raise PostMergeCommissioningSettingsError("host_instance must be kis-op")
        if _NAMESPACE.fullmatch(self.state_namespace) is None:
            raise PostMergeCommissioningSettingsError("state_namespace is invalid")
        if not self.targets:
            raise PostMergeCommissioningSettingsError("targets must not be empty")
        if not self.surfaces:
            raise PostMergeCommissioningSettingsError("surfaces must not be empty")
        repositories = [item.repository.casefold() for item in self.targets]
        if len(set(repositories)) != len(repositories):
            raise PostMergeCommissioningSettingsError("targets contains duplicate repository values")
        surface_ids = [item.id for item in self.surfaces]
        if len(set(surface_ids)) != len(surface_ids):
            raise PostMergeCommissioningSettingsError("surfaces contains duplicate surface values")
        object.__setattr__(self, "targets", tuple(sorted(self.targets, key=lambda item: item.repository.casefold())))
        object.__setattr__(self, "surfaces", tuple(sorted(self.surfaces, key=lambda item: item.id)))
        object.__setattr__(
            self,
            "ambiguous_risk_triggers",
            tuple(sorted(self.ambiguous_risk_triggers)),
        )


def _load_document(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PostMergeCommissioningSettingsError(
            f"post-merge commissioning settings are missing: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise PostMergeCommissioningSettingsError(
            f"invalid JSON in post-merge commissioning settings {path}: {exc}"
        ) from exc
    if not isinstance(value, Mapping):
        raise PostMergeCommissioningSettingsError(
            "post-merge commissioning settings root must be an object"
        )
    return value


def _target(value: Any, index: int) -> PostMergeTargetSettings:
    label = f"targets[{index}]"
    if not isinstance(value, Mapping):
        raise PostMergeCommissioningSettingsError(f"{label} must be an object")
    _exact_keys(value, _TARGET_KEYS, label)
    return PostMergeTargetSettings(
        project_id=_text(value["project_id"], f"{label}.project_id"),
        repository=_text(value["repository"], f"{label}.repository"),
        default_branch=_text(value["default_branch"], f"{label}.default_branch"),
    )


def _surface(value: Any, index: int) -> CommissioningSurfaceSettings:
    label = f"surfaces[{index}]"
    if not isinstance(value, Mapping):
        raise PostMergeCommissioningSettingsError(f"{label} must be an object")
    _exact_keys(value, _SURFACE_KEYS, label)
    patterns = _string_array(value["path_patterns"], f"{label}.path_patterns")
    normalized_patterns = tuple(
        _path_pattern(item, f"{label}.path_patterns") for item in patterns
    )
    risks = _validate_risks(
        _string_array(value["risk_triggers"], f"{label}.risk_triggers"),
        f"{label}.risk_triggers",
    )
    return CommissioningSurfaceSettings(
        id=_text(value["id"], f"{label}.id"),
        path_patterns=normalized_patterns,
        risk_triggers=risks,
        runtime_instance=_text(value["runtime_instance"], f"{label}.runtime_instance"),
        refresh_rule=_text(value["refresh_rule"], f"{label}.refresh_rule"),
        verification_procedure=_text(
            value["verification_procedure"], f"{label}.verification_procedure"
        ),
        expected_invariant=_text(
            value["expected_invariant"], f"{label}.expected_invariant"
        ),
        evidence_target=_text(value["evidence_target"], f"{label}.evidence_target"),
        terminal_success_criterion=_text(
            value["terminal_success_criterion"], f"{label}.terminal_success_criterion"
        ),
    )


def load_post_merge_commissioning_settings(
    path: Path | None = None,
) -> PostMergeCommissioningSettings:
    target = path or (
        Path(__file__).resolve().parents[3]
        / "settings"
        / "post-merge-commissioning.settings.json"
    )
    document = _load_document(target)
    _exact_keys(document, _ROOT_KEYS, "root")
    if document["schema_version"] != 1:
        raise PostMergeCommissioningSettingsError("schema_version must be 1")
    targets = document["targets"]
    surfaces = document["surfaces"]
    if not isinstance(targets, Sequence) or isinstance(targets, (str, bytes, bytearray)):
        raise PostMergeCommissioningSettingsError("targets must be an array")
    if not isinstance(surfaces, Sequence) or isinstance(surfaces, (str, bytes, bytearray)):
        raise PostMergeCommissioningSettingsError("surfaces must be an array")
    ambiguous = _validate_risks(
        _string_array(document["ambiguous_risk_triggers"], "ambiguous_risk_triggers"),
        "ambiguous_risk_triggers",
    )
    return PostMergeCommissioningSettings(
        schema_version=1,
        enabled=document["enabled"],
        host_instance=_text(document["host_instance"], "host_instance"),
        state_namespace=_text(document["state_namespace"], "state_namespace"),
        receipt_retention=_integer(document["receipt_retention"], "receipt_retention", 1, 1000),
        freshness_stale_after_seconds=_integer(
            document["freshness_stale_after_seconds"],
            "freshness_stale_after_seconds",
            60,
            604800,
        ),
        poll_interval_seconds=_integer(
            document["poll_interval_seconds"], "poll_interval_seconds", 60, 86400
        ),
        initial_delay_seconds=_integer(
            document["initial_delay_seconds"], "initial_delay_seconds", 0, 3600
        ),
        overlap_seconds=_integer(document["overlap_seconds"], "overlap_seconds", 0, 86400),
        max_candidates=_integer(document["max_candidates"], "max_candidates", 1, 1000),
        max_external_reads=_integer(
            document["max_external_reads"], "max_external_reads", 1, 10000
        ),
        max_mutations=_integer(document["max_mutations"], "max_mutations", 1, 1000),
        ambiguous_risk_triggers=ambiguous,
        targets=tuple(_target(item, index) for index, item in enumerate(targets)),
        surfaces=tuple(_surface(item, index) for index, item in enumerate(surfaces)),
    )


__all__ = [
    "CommissioningSurfaceSettings",
    "PostMergeCommissioningSettings",
    "PostMergeCommissioningSettingsError",
    "PostMergeTargetSettings",
    "load_post_merge_commissioning_settings",
]
