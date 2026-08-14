from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping

_PROJECT_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_LOGICAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SECRET_NAME = re.compile(r"(?:token|secret|password|credential|api[_-]?key|authorization|auth)", re.IGNORECASE)
_ROOT_KEYS = {"schema_version", "provider", "limits", "authorizations"}
_PROVIDER_KEYS = {"project_id", "script_relative_path"}
_LIMIT_KEYS = {"max_parameters", "max_parameter_string_chars", "max_request_json_chars"}
_AUTH_KEYS = {"project_id", "profiles"}
_PROFILE_KEYS = {
    "profile_id",
    "approval_required",
    "recipe_directory",
    "recipe_id_prefix",
    "allowed_parameter_keys",
}


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    unknown = sorted(set(value) - expected)
    missing = sorted(expected - set(value))
    if unknown:
        raise ValueError(f"unknown {label} keys: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"missing {label} keys: {', '.join(missing)}")


def _project_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or _PROJECT_ID.fullmatch(value) is None:
        raise ValueError(f"{label} must use lower-case kebab-case")
    return value


def _logical_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or _LOGICAL_ID.fullmatch(value) is None:
        raise ValueError(f"{label} must be a safe logical identifier")
    return value


def _relative_windows_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty relative path")
    path = PureWindowsPath(value.strip())
    if path.is_absolute() or path.drive or ".." in path.parts:
        raise ValueError(f"{label} must be relative without parent traversal")
    normalized = str(path)
    if normalized in {"", "."}:
        raise ValueError(f"{label} must identify a child path")
    return normalized


def _bounded_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer from {minimum} to {maximum}")
    return value


@dataclass(frozen=True, slots=True)
class AcquisitionLimits:
    max_parameters: int
    max_parameter_string_chars: int
    max_request_json_chars: int


@dataclass(frozen=True, slots=True)
class ProfileAuthorization:
    profile_id: str
    approval_required: bool
    recipe_directory: str
    recipe_id_prefix: str
    allowed_parameter_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProjectAuthorization:
    project_id: str
    profiles: tuple[ProfileAuthorization, ...]


@dataclass(frozen=True, slots=True)
class ExternalAcquisitionSettings:
    provider_project_id: str
    provider_script_relative_path: str
    limits: AcquisitionLimits
    authorizations: tuple[ProjectAuthorization, ...]

    def authorization(self, project_id: str, profile_id: str) -> ProfileAuthorization:
        for project in self.authorizations:
            if project.project_id != project_id:
                continue
            for profile in project.profiles:
                if profile.profile_id == profile_id:
                    return profile
        raise KeyError((project_id, profile_id))


def _profile(value: Any, label: str) -> ProfileAuthorization:
    raw = _mapping(value, label)
    _exact_keys(raw, _PROFILE_KEYS, label)
    profile_id = _project_id(raw["profile_id"], f"{label}.profile_id")
    if raw["approval_required"] is not True:
        raise ValueError(f"{label}.approval_required must be true")
    recipe_directory = _relative_windows_path(raw["recipe_directory"], f"{label}.recipe_directory")
    prefix = _logical_id(raw["recipe_id_prefix"], f"{label}.recipe_id_prefix")
    keys = raw["allowed_parameter_keys"]
    if not isinstance(keys, list) or len(keys) > 64:
        raise ValueError(f"{label}.allowed_parameter_keys must be an array with at most 64 entries")
    normalized = tuple(_logical_id(item, f"{label}.allowed_parameter_keys") for item in keys)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{label}.allowed_parameter_keys must be unique")
    if any(_SECRET_NAME.search(item) for item in normalized):
        raise ValueError(f"{label}.allowed_parameter_keys cannot contain secret-like names")
    return ProfileAuthorization(
        profile_id=profile_id,
        approval_required=True,
        recipe_directory=recipe_directory,
        recipe_id_prefix=prefix,
        allowed_parameter_keys=normalized,
    )


def load_external_acquisition_settings(path: Path | None = None) -> ExternalAcquisitionSettings:
    source = path or Path(__file__).resolve().parents[3] / "settings" / "external-acquisition.settings.json"
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"external acquisition settings could not be read: {type(exc).__name__}") from exc
    root = _mapping(payload, "external acquisition settings")
    _exact_keys(root, _ROOT_KEYS, "external acquisition settings")
    if root["schema_version"] != 1:
        raise ValueError("external acquisition settings schema_version must be 1")

    provider = _mapping(root["provider"], "provider")
    _exact_keys(provider, _PROVIDER_KEYS, "provider")
    provider_project_id = _project_id(provider["project_id"], "provider.project_id")
    provider_script = _relative_windows_path(provider["script_relative_path"], "provider.script_relative_path")

    limits_raw = _mapping(root["limits"], "limits")
    _exact_keys(limits_raw, _LIMIT_KEYS, "limits")
    limits = AcquisitionLimits(
        max_parameters=_bounded_int(limits_raw["max_parameters"], "limits.max_parameters", 1, 64),
        max_parameter_string_chars=_bounded_int(limits_raw["max_parameter_string_chars"], "limits.max_parameter_string_chars", 1, 4096),
        max_request_json_chars=_bounded_int(limits_raw["max_request_json_chars"], "limits.max_request_json_chars", 1024, 65536),
    )

    raw_authorizations = root["authorizations"]
    if not isinstance(raw_authorizations, list) or not raw_authorizations:
        raise ValueError("authorizations must be a non-empty array")
    projects: list[ProjectAuthorization] = []
    for index, item in enumerate(raw_authorizations):
        label = f"authorizations[{index}]"
        raw = _mapping(item, label)
        _exact_keys(raw, _AUTH_KEYS, label)
        project_id = _project_id(raw["project_id"], f"{label}.project_id")
        raw_profiles = raw["profiles"]
        if not isinstance(raw_profiles, list) or not raw_profiles:
            raise ValueError(f"{label}.profiles must be a non-empty array")
        profiles = tuple(_profile(profile, f"{label}.profiles[{i}]") for i, profile in enumerate(raw_profiles))
        profile_ids = [profile.profile_id for profile in profiles]
        if len(set(profile_ids)) != len(profile_ids):
            raise ValueError(f"{label}.profiles profile_id values must be unique")
        projects.append(ProjectAuthorization(project_id=project_id, profiles=profiles))
    project_ids = [project.project_id for project in projects]
    if len(set(project_ids)) != len(project_ids):
        raise ValueError("authorizations project_id values must be unique")

    return ExternalAcquisitionSettings(
        provider_project_id=provider_project_id,
        provider_script_relative_path=provider_script,
        limits=limits,
        authorizations=tuple(projects),
    )


__all__ = [
    "AcquisitionLimits",
    "ExternalAcquisitionSettings",
    "ProfileAuthorization",
    "ProjectAuthorization",
    "load_external_acquisition_settings",
]
