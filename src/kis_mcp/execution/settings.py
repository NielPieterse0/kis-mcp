from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

from ..config import APPROVED_STATE_ROOT
from ..paths import is_within_windows_boundary

_LOGICAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]{1,127}$")
_ROOT_KEYS = frozenset({"schema_version", "default_profile", "evidence_limit_chars", "profiles"})
_LOCAL_KEYS = frozenset({"profile_id", "backend_id", "enabled", "image_id", "toolchain_id"})
_HYPERV_KEYS = frozenset((*_LOCAL_KEYS, "hyperv"))
_HYPERV_CONFIG_KEYS = frozenset(
    {
        "template_vm",
        "checkpoint_name",
        "state_root",
        "guest_workspace",
        "guest_username_env",
        "guest_password_env",
        "startup_timeout_ms",
        "cleanup_timeout_ms",
    }
)


class ExecutionSettingsError(RuntimeError):
    pass


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ExecutionSettingsError(f"{label} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    actual = {str(key) for key in value}
    unknown = sorted(actual - expected)
    missing = sorted(expected - actual)
    if unknown:
        raise ExecutionSettingsError(f"{label} has unknown keys: {unknown}")
    if missing:
        raise ExecutionSettingsError(f"{label} is missing required keys: {missing}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExecutionSettingsError(f"{label} must be a non-empty string")
    return value.strip()


def _logical_id(value: Any, label: str) -> str:
    text = _text(value, label)
    if _LOGICAL_ID.fullmatch(text) is None:
        raise ExecutionSettingsError(f"{label} must be a safe logical identifier")
    return text


def _positive_int(value: Any, label: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ExecutionSettingsError(f"{label} must be an integer from 1 to {maximum}")
    return value


def _windows_absolute(value: Any, label: str) -> str:
    text = _text(value, label)
    path = PureWindowsPath(text)
    if not path.is_absolute() or not path.drive:
        raise ExecutionSettingsError(f"{label} must be an absolute Windows path")
    return str(path)


def _env_name(value: Any, label: str) -> str:
    text = _text(value, label)
    if _ENV_NAME.fullmatch(text) is None:
        raise ExecutionSettingsError(f"{label} must be an uppercase environment variable name")
    return text


@dataclass(frozen=True, slots=True)
class HyperVProfileSettings:
    template_vm: str
    checkpoint_name: str
    state_root: str
    guest_workspace: str
    guest_username_env: str
    guest_password_env: str
    startup_timeout_ms: int
    cleanup_timeout_ms: int

    def __post_init__(self) -> None:
        state_root = _windows_absolute(self.state_root, "hyperv.state_root")
        if not is_within_windows_boundary(state_root, boundary=APPROVED_STATE_ROOT):
            raise ExecutionSettingsError(
                "hyperv.state_root must remain within the configured KIS state root"
            )
        object.__setattr__(self, "state_root", state_root)


@dataclass(frozen=True, slots=True)
class RunnerProfileSettings:
    profile_id: str
    backend_id: str
    enabled: bool
    image_id: str
    toolchain_id: str
    hyperv: HyperVProfileSettings | None = None


@dataclass(frozen=True, slots=True)
class ExecutionRunnerSettings:
    default_profile: str
    evidence_limit_chars: int
    profiles: tuple[RunnerProfileSettings, ...]

    def profile(self, profile_id: str) -> RunnerProfileSettings:
        for profile in self.profiles:
            if profile.profile_id == profile_id:
                return profile
        raise KeyError(profile_id)


def _hyperv_settings(raw: Any, label: str) -> HyperVProfileSettings:
    value = _mapping(raw, label)
    _exact_keys(value, _HYPERV_CONFIG_KEYS, label)
    state_root = _windows_absolute(value["state_root"], f"{label}.state_root")
    if not is_within_windows_boundary(state_root, boundary=APPROVED_STATE_ROOT):
        raise ExecutionSettingsError(
            f"{label}.state_root must remain within the configured KIS state root"
        )
    return HyperVProfileSettings(
        template_vm=_text(value["template_vm"], f"{label}.template_vm"),
        checkpoint_name=_text(value["checkpoint_name"], f"{label}.checkpoint_name"),
        state_root=state_root,
        guest_workspace=_windows_absolute(value["guest_workspace"], f"{label}.guest_workspace"),
        guest_username_env=_env_name(value["guest_username_env"], f"{label}.guest_username_env"),
        guest_password_env=_env_name(value["guest_password_env"], f"{label}.guest_password_env"),
        startup_timeout_ms=_positive_int(
            value["startup_timeout_ms"], f"{label}.startup_timeout_ms", 600_000
        ),
        cleanup_timeout_ms=_positive_int(
            value["cleanup_timeout_ms"], f"{label}.cleanup_timeout_ms", 600_000
        ),
    )


def _profile(raw: Any, index: int) -> RunnerProfileSettings:
    label = f"profiles[{index}]"
    value = _mapping(raw, label)
    backend = _logical_id(value.get("backend_id"), f"{label}.backend_id")
    expected = _HYPERV_KEYS if backend == "windows-hyperv" else _LOCAL_KEYS
    _exact_keys(value, expected, label)
    if backend not in {"local-process", "windows-hyperv"}:
        raise ExecutionSettingsError(f"{label}.backend_id is unsupported")
    enabled = value["enabled"]
    if not isinstance(enabled, bool):
        raise ExecutionSettingsError(f"{label}.enabled must be a boolean")
    hyperv = (
        _hyperv_settings(value["hyperv"], f"{label}.hyperv")
        if backend == "windows-hyperv"
        else None
    )
    return RunnerProfileSettings(
        profile_id=_logical_id(value["profile_id"], f"{label}.profile_id"),
        backend_id=backend,
        enabled=enabled,
        image_id=_logical_id(value["image_id"], f"{label}.image_id"),
        toolchain_id=_logical_id(value["toolchain_id"], f"{label}.toolchain_id"),
        hyperv=hyperv,
    )


def load_execution_runner_settings(path: Path | None = None) -> ExecutionRunnerSettings:
    source = path or Path(__file__).resolve().parents[3] / "settings" / "execution-runners.settings.json"
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutionSettingsError(
            f"execution runner settings could not be read: {type(exc).__name__}"
        ) from exc
    root = _mapping(document, "execution runner settings")
    _exact_keys(root, _ROOT_KEYS, "execution runner settings")
    if root["schema_version"] != 1:
        raise ExecutionSettingsError("execution runner settings schema_version must be 1")
    raw_profiles = root["profiles"]
    if not isinstance(raw_profiles, list) or not raw_profiles:
        raise ExecutionSettingsError("profiles must be a non-empty array")
    profiles = tuple(_profile(item, index) for index, item in enumerate(raw_profiles))
    ids = [profile.profile_id for profile in profiles]
    if len(set(ids)) != len(ids):
        raise ExecutionSettingsError("profiles profile_id values must be unique")
    default = _logical_id(root["default_profile"], "default_profile")
    if default not in ids:
        raise ExecutionSettingsError("default_profile must identify a configured profile")
    if not next(profile for profile in profiles if profile.profile_id == default).enabled:
        raise ExecutionSettingsError("default_profile must be enabled")
    return ExecutionRunnerSettings(
        default_profile=default,
        evidence_limit_chars=_positive_int(
            root["evidence_limit_chars"], "evidence_limit_chars", 500_000
        ),
        profiles=profiles,
    )


__all__ = [
    "ExecutionRunnerSettings",
    "ExecutionSettingsError",
    "HyperVProfileSettings",
    "RunnerProfileSettings",
    "load_execution_runner_settings",
]
