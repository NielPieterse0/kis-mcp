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
    approval_register_path: Path = Path(r"C:\Projects\kis-mcp\docs\HARD-BLOCK-APPROVAL-REGISTER.md")
    discover_enabled: bool = True
    max_approval_entries: int = 20
    max_recent_calls: int = 50
    max_policy_decisions: int = 50
    max_active_processes: int = 50
    max_active_searches: int = 50
    max_discover_findings: int = 20


_ROOT_FIELDS = frozenset(
    {
        "schema_version",
        "project_path",
        "runtime_settings_path",
        "policy_path",
        "provider_settings_path",
        "approval_register_path",
        "quarantine_root",
        "verification_command",
        "discover_enabled",
        "limits",
    }
)
_LIMIT_FIELDS = frozenset(
    {
        "max_provider_entries",
        "max_approval_entries",
        "max_recent_calls",
        "max_policy_decisions",
        "max_active_processes",
        "max_active_searches",
        "max_discover_findings",
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


def load_control_center_settings(path: str | Path | None = None) -> ControlCenterSettings:
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
    if type(raw["discover_enabled"]) is not bool:
        raise ControlCenterSettingsError("discover_enabled must be a boolean")
    limits = raw["limits"]
    if not isinstance(limits, dict):
        raise ControlCenterSettingsError("limits must be a JSON object")
    _require_exact_fields(limits, _LIMIT_FIELDS, "limits")
    verification_command = raw["verification_command"]
    if (
        not isinstance(verification_command, list)
        or not verification_command
        or any(type(item) is not str or not item for item in verification_command)
    ):
        raise ControlCenterSettingsError(
            "verification_command must be a non-empty array of non-empty strings"
        )
    return ControlCenterSettings(
        schema_version=1,
        project_path=_absolute_path(raw["project_path"], "project_path"),
        runtime_settings_path=_absolute_path(
            raw["runtime_settings_path"], "runtime_settings_path"
        ),
        policy_path=_absolute_path(raw["policy_path"], "policy_path"),
        provider_settings_path=_absolute_path(
            raw["provider_settings_path"], "provider_settings_path"
        ),
        approval_register_path=_absolute_path(
            raw["approval_register_path"], "approval_register_path"
        ),
        quarantine_root=_absolute_path(raw["quarantine_root"], "quarantine_root"),
        verification_command=tuple(verification_command),
        discover_enabled=raw["discover_enabled"],
        max_provider_entries=_bounded_integer(
            limits["max_provider_entries"], "limits.max_provider_entries", 1, 100
        ),
        max_approval_entries=_bounded_integer(
            limits["max_approval_entries"], "limits.max_approval_entries", 1, 100
        ),
        max_recent_calls=_bounded_integer(
            limits["max_recent_calls"], "limits.max_recent_calls", 1, 200
        ),
        max_policy_decisions=_bounded_integer(
            limits["max_policy_decisions"], "limits.max_policy_decisions", 1, 200
        ),
        max_active_processes=_bounded_integer(
            limits["max_active_processes"], "limits.max_active_processes", 1, 100
        ),
        max_active_searches=_bounded_integer(
            limits["max_active_searches"], "limits.max_active_searches", 1, 100
        ),
        max_discover_findings=_bounded_integer(
            limits["max_discover_findings"], "limits.max_discover_findings", 1, 100
        ),
        max_quarantine_records=_bounded_integer(
            limits["max_quarantine_records"], "limits.max_quarantine_records", 1, 500
        ),
        git_timeout_seconds=_bounded_integer(
            limits["git_timeout_seconds"], "limits.git_timeout_seconds", 1, 30
        ),
        max_json_bytes=_bounded_integer(
            limits["max_json_bytes"], "limits.max_json_bytes", 1024, 10_000_000
        ),
    )


def _require_exact_fields(document: dict[str, Any], expected: frozenset[str], label: str) -> None:
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


def _bounded_integer(value: Any, field: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise ControlCenterSettingsError(
            f"{field} must be an integer between {minimum} and {maximum}"
        )
    return value
