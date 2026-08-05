from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ControlCenterSettingsError(ValueError):
    """Raised when Control Center settings are missing or structurally invalid."""


@dataclass(frozen=True, slots=True)
class ControlCenterSettings:
    schema_version: int
    project_path: Path
    runtime_settings_path: Path
    policy_path: Path
    provider_settings_path: Path
    quarantine_root: Path
    verification_command: tuple[str, ...]
    max_provider_entries: int
    max_quarantine_records: int
    git_timeout_seconds: int
    max_json_bytes: int


_ROOT_FIELDS = frozenset(
    {
        "schema_version",
        "project_path",
        "runtime_settings_path",
        "policy_path",
        "provider_settings_path",
        "quarantine_root",
        "verification_command",
        "limits",
    }
)
_LIMIT_FIELDS = frozenset(
    {
        "max_provider_entries",
        "max_quarantine_records",
        "git_timeout_seconds",
        "max_json_bytes",
    }
)


def default_control_center_settings_path() -> Path:
    configured = os.environ.get("KIS_CONTROL_CENTER_SETTINGS")
    if configured:
        return Path(configured)

    checkout_candidate = Path.cwd() / "settings" / "control-center.settings.json"
    if checkout_candidate.is_file():
        return checkout_candidate

    return Path(__file__).resolve().parents[3] / "settings" / "control-center.settings.json"


def load_control_center_settings(
    path: str | Path | None = None,
) -> ControlCenterSettings:
    settings_path = Path(path) if path is not None else default_control_center_settings_path()
    try:
        raw: Any = json.loads(settings_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ControlCenterSettingsError(
            f"Control Center settings are unreadable: {settings_path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ControlCenterSettingsError(
            f"Control Center settings are not valid JSON: {settings_path}: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise ControlCenterSettingsError("Control Center settings must be a JSON object")
    _require_exact_fields(raw, _ROOT_FIELDS, "settings")

    if type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
        raise ControlCenterSettingsError("schema_version must be integer 1")

    limits = raw["limits"]
    if not isinstance(limits, dict):
        raise ControlCenterSettingsError("limits must be a JSON object")
    _require_exact_fields(limits, _LIMIT_FIELDS, "limits")

    project_path = _absolute_path(raw["project_path"], "project_path")
    runtime_settings_path = _absolute_path(
        raw["runtime_settings_path"], "runtime_settings_path"
    )
    policy_path = _absolute_path(raw["policy_path"], "policy_path")
    provider_settings_path = _absolute_path(
        raw["provider_settings_path"], "provider_settings_path"
    )
    quarantine_root = _absolute_path(raw["quarantine_root"], "quarantine_root")

    verification_command = raw["verification_command"]
    if (
        not isinstance(verification_command, list)
        or not verification_command
        or any(type(item) is not str or not item for item in verification_command)
    ):
        raise ControlCenterSettingsError(
            "verification_command must be a non-empty array of non-empty strings"
        )

    max_provider_entries = _bounded_integer(
        limits["max_provider_entries"],
        "limits.max_provider_entries",
        minimum=1,
        maximum=100,
    )
    max_quarantine_records = _bounded_integer(
        limits["max_quarantine_records"],
        "limits.max_quarantine_records",
        minimum=1,
        maximum=500,
    )
    git_timeout_seconds = _bounded_integer(
        limits["git_timeout_seconds"],
        "limits.git_timeout_seconds",
        minimum=1,
        maximum=30,
    )
    max_json_bytes = _bounded_integer(
        limits["max_json_bytes"],
        "limits.max_json_bytes",
        minimum=1024,
        maximum=10_000_000,
    )

    return ControlCenterSettings(
        schema_version=1,
        project_path=project_path,
        runtime_settings_path=runtime_settings_path,
        policy_path=policy_path,
        provider_settings_path=provider_settings_path,
        quarantine_root=quarantine_root,
        verification_command=tuple(verification_command),
        max_provider_entries=max_provider_entries,
        max_quarantine_records=max_quarantine_records,
        git_timeout_seconds=git_timeout_seconds,
        max_json_bytes=max_json_bytes,
    )


def _require_exact_fields(
    document: dict[str, Any], expected: frozenset[str], label: str
) -> None:
    actual = set(document)
    unknown = sorted(actual - expected)
    missing = sorted(expected - actual)
    if unknown:
        raise ControlCenterSettingsError(
            f"{label} contains unknown field(s): {', '.join(unknown)}"
        )
    if missing:
        raise ControlCenterSettingsError(
            f"{label} is missing required field(s): {', '.join(missing)}"
        )


def _absolute_path(value: Any, field: str) -> Path:
    if type(value) is not str or not value:
        raise ControlCenterSettingsError(f"{field} must be a non-empty string")
    path = Path(value)
    if not path.is_absolute():
        raise ControlCenterSettingsError(f"{field} must be an absolute path")
    return path


def _bounded_integer(value: Any, field: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise ControlCenterSettingsError(
            f"{field} must be an integer between {minimum} and {maximum}"
        )
    return value
