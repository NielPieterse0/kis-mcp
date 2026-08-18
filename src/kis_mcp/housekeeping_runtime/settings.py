from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kis_mcp.housekeeping import RunnerKind
from kis_mcp.paths import is_within_windows_boundary, normalize_windows_path

_PROJECT_BOUNDARY = r"C:\Projects"
_ROOT_KEYS = frozenset(
    {
        "schema_version",
        "enabled",
        "host_instance",
        "state_namespace",
        "receipt_retention",
        "freshness_stale_after_seconds",
        "apply_max_age_seconds",
        "scheduled_mode",
        "targets",
    }
)
_TARGET_KEYS = frozenset(
    {
        "runner",
        "project_id",
        "repository",        "repository_root",
        "interval_seconds",
        "initial_delay_seconds",
        "item_limit",
        "max_findings",
        "max_mutations",
        "max_external_reads",
    }
)
_RUNNER_NAMES = {
    "work-management-reconciliation": RunnerKind.WORK_MANAGEMENT_RECONCILIATION,
    "backlog-readiness": RunnerKind.BACKLOG_READINESS,
}
_NAMESPACE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_PROJECT_ID = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class HousekeepingRuntimeSettingsError(RuntimeError):
    pass


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    actual = {str(key) for key in value}
    unknown = sorted(actual - expected)
    missing = sorted(expected - actual)
    if unknown:
        raise HousekeepingRuntimeSettingsError(f"{label} has unknown keys: {unknown}")
    if missing:
        raise HousekeepingRuntimeSettingsError(f"{label} is missing required keys: {missing}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HousekeepingRuntimeSettingsError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise HousekeepingRuntimeSettingsError(f"{label} must be an integer")
    if not minimum <= value <= maximum:
        raise HousekeepingRuntimeSettingsError(
            f"{label} must be between {minimum} and {maximum}"
        )
    return value


def _runner(value: Any, label: str) -> RunnerKind:
    name = _text(value, label)
    try:
        return _RUNNER_NAMES[name]
    except KeyError as exc:
        raise HousekeepingRuntimeSettingsError(
            f"{label} must identify a supported housekeeping runner"
        ) from exc


@dataclass(frozen=True, slots=True)
class HousekeepingTargetSettings:
    runner: RunnerKind
    project_id: str
    repository: str
    repository_root: str
    interval_seconds: int
    initial_delay_seconds: int
    item_limit: int
    max_findings: int
    max_mutations: int
    max_external_reads: int

    def __post_init__(self) -> None:
        if not isinstance(self.runner, RunnerKind):
            raise HousekeepingRuntimeSettingsError("runner must be a RunnerKind")
        project_id = _text(self.project_id, "project_id")
        if _PROJECT_ID.fullmatch(project_id) is None:
            raise HousekeepingRuntimeSettingsError("project_id must use lower-case kebab-case")
        repository = _text(self.repository, "repository")
        if _REPOSITORY.fullmatch(repository) is None:
            raise HousekeepingRuntimeSettingsError("repository must be owner/name")
        root = normalize_windows_path(
            _text(self.repository_root, "repository_root"), base=_PROJECT_BOUNDARY
        )
        if not is_within_windows_boundary(root, boundary=_PROJECT_BOUNDARY):
            raise HousekeepingRuntimeSettingsError(
                "repository_root must remain beneath C:\\Projects"
            )
        object.__setattr__(self, "project_id", project_id)
        object.__setattr__(self, "repository", repository)
        object.__setattr__(self, "repository_root", root)


@dataclass(frozen=True, slots=True)
class HousekeepingRuntimeSettings:
    enabled: bool
    host_instance: str
    state_namespace: str
    receipt_retention: int
    freshness_stale_after_seconds: int
    apply_max_age_seconds: int
    scheduled_mode: str
    targets: tuple[HousekeepingTargetSettings, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise HousekeepingRuntimeSettingsError("schema_version must be 1")
        if not isinstance(self.enabled, bool):
            raise HousekeepingRuntimeSettingsError("enabled must be a boolean")
        if self.host_instance != "kis-op":
            raise HousekeepingRuntimeSettingsError("host_instance must be kis-op")
        if _NAMESPACE.fullmatch(self.state_namespace) is None:
            raise HousekeepingRuntimeSettingsError("state_namespace is invalid")
        if self.scheduled_mode != "preview":
            raise HousekeepingRuntimeSettingsError("scheduled_mode must be preview")
        if not self.targets:
            raise HousekeepingRuntimeSettingsError("targets must not be empty")
        runner_values = [item.runner for item in self.targets]
        if len(set(runner_values)) != len(runner_values):
            raise HousekeepingRuntimeSettingsError("targets contains duplicate runner values")
        object.__setattr__(
            self,
            "targets",
            tuple(sorted(self.targets, key=lambda item: item.runner.value)),
        )

    def target(self, runner: str | RunnerKind) -> HousekeepingTargetSettings:
        selected = runner if isinstance(runner, RunnerKind) else _runner(runner, "runner")
        for target in self.targets:
            if target.runner is selected:
                return target
        raise KeyError(selected.value)


def _load_document(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HousekeepingRuntimeSettingsError(
            f"housekeeping settings are missing: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise HousekeepingRuntimeSettingsError(
            f"invalid JSON in housekeeping settings {path}: {exc}"
        ) from exc
    if not isinstance(value, Mapping):
        raise HousekeepingRuntimeSettingsError("housekeeping settings root must be an object")
    return value


def _target(value: Any, index: int) -> HousekeepingTargetSettings:
    label = f"targets[{index}]"
    if not isinstance(value, Mapping):
        raise HousekeepingRuntimeSettingsError(f"{label} must be an object")
    _exact_keys(value, _TARGET_KEYS, label)
    return HousekeepingTargetSettings(
        runner=_runner(value["runner"], f"{label}.runner"),
        project_id=_text(value["project_id"], f"{label}.project_id"),
        repository=_text(value["repository"], f"{label}.repository"),
        repository_root=_text(value["repository_root"], f"{label}.repository_root"),
        interval_seconds=_integer(
            value["interval_seconds"], f"{label}.interval_seconds", 60, 86400
        ),
        initial_delay_seconds=_integer(
            value["initial_delay_seconds"], f"{label}.initial_delay_seconds", 0, 3600
        ),
        item_limit=_integer(value["item_limit"], f"{label}.item_limit", 1, 10000),
        max_findings=_integer(
            value["max_findings"], f"{label}.max_findings", 1, 1000
        ),
        max_mutations=_integer(
            value["max_mutations"], f"{label}.max_mutations", 1, 100
        ),
        max_external_reads=_integer(
            value["max_external_reads"], f"{label}.max_external_reads", 1, 1000
        ),
    )


def load_housekeeping_runtime_settings(
    path: Path | None = None,
) -> HousekeepingRuntimeSettings:
    target = path or (
        Path(__file__).resolve().parents[3] / "settings" / "housekeeping.settings.json"
    )
    document = _load_document(target)
    _exact_keys(document, _ROOT_KEYS, "root")
    if document["schema_version"] != 1:
        raise HousekeepingRuntimeSettingsError("schema_version must be 1")
    targets = document["targets"]
    if not isinstance(targets, Sequence) or isinstance(
        targets, (str, bytes, bytearray)
    ):
        raise HousekeepingRuntimeSettingsError("targets must be an array")
    return HousekeepingRuntimeSettings(
        schema_version=1,
        enabled=document["enabled"],
        host_instance=_text(document["host_instance"], "host_instance"),
        state_namespace=_text(document["state_namespace"], "state_namespace"),
        receipt_retention=_integer(
            document["receipt_retention"], "receipt_retention", 1, 1000
        ),
        freshness_stale_after_seconds=_integer(
            document["freshness_stale_after_seconds"],
            "freshness_stale_after_seconds",
            60,
            604800,
        ),
        apply_max_age_seconds=_integer(
            document["apply_max_age_seconds"], "apply_max_age_seconds", 1, 86400
        ),
        scheduled_mode=_text(document["scheduled_mode"], "scheduled_mode"),
        targets=tuple(_target(item, index) for index, item in enumerate(targets)),
    )


__all__ = [
    "HousekeepingRuntimeSettings",
    "HousekeepingRuntimeSettingsError",
    "HousekeepingTargetSettings",
    "load_housekeeping_runtime_settings",
]
