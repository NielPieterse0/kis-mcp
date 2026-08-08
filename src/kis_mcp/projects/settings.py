from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path, PureWindowsPath
from typing import Any

from .contracts import (
    GitHubProjectBinding,
    GitHubProjectResource,
    ProjectDefinition,
    SupabaseProjectBinding,
    normalize_windows_root,
)
from .registry import ProjectRegistry

_ROOT_KEYS = {"schema_version", "default_project_id", "projects"}
_PROJECT_KEYS = {"project_id", "display_name", "local_root", "github", "supabase"}
_GITHUB_KEYS = {"repository", "projects"}
_GITHUB_PROJECT_KEYS = {"binding_id", "owner", "owner_type", "project_number"}
_SUPABASE_KEYS = {"project_ref"}


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


def _project_within_boundary(local_root: str, boundary: str) -> None:
    root = PureWindowsPath(normalize_windows_root(local_root))
    approved = PureWindowsPath(normalize_windows_root(boundary, "project boundary"))
    try:
        root.relative_to(approved)
    except ValueError as exc:
        raise ValueError(
            f"project local_root must remain within approved project boundary: {approved}"
        ) from exc


def _github(value: Any, label: str) -> GitHubProjectBinding | None:
    if value is None:
        return None
    raw = _mapping(value, label)
    _exact_keys(raw, _GITHUB_KEYS, label)
    raw_projects = raw["projects"]
    if not isinstance(raw_projects, list):
        raise ValueError(f"{label}.projects must be an array")
    projects: list[GitHubProjectResource] = []
    for index, item in enumerate(raw_projects):
        project = _mapping(item, f"{label}.projects[{index}]")
        _exact_keys(project, _GITHUB_PROJECT_KEYS, f"{label}.projects[{index}]")
        projects.append(
            GitHubProjectResource(
                binding_id=project["binding_id"],
                owner=project["owner"],
                owner_type=project["owner_type"],
                project_number=project["project_number"],
            )
        )
    return GitHubProjectBinding(
        repository=raw["repository"],
        projects=tuple(projects),
    )


def _supabase(value: Any, label: str) -> SupabaseProjectBinding | None:
    if value is None:
        return None
    raw = _mapping(value, label)
    _exact_keys(raw, _SUPABASE_KEYS, label)
    return SupabaseProjectBinding(project_ref=raw["project_ref"])


def load_project_registry_settings(
    path: Path | None = None,
    *,
    boundary: str = "C:\\Projects",
) -> ProjectRegistry:
    source = path or Path(__file__).resolve().parents[3] / "settings" / "projects.settings.json"
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"project registry settings could not be read: {type(exc).__name__}"
        ) from exc
    root = _mapping(payload, "project registry")
    _exact_keys(root, _ROOT_KEYS, "project registry")
    if root["schema_version"] != 1:
        raise ValueError("project registry schema_version must be 1")
    raw_projects = root["projects"]
    if not isinstance(raw_projects, list) or not raw_projects:
        raise ValueError("project registry projects must be a non-empty array")

    projects: list[ProjectDefinition] = []
    for index, item in enumerate(raw_projects):
        raw = _mapping(item, f"projects[{index}]")
        _exact_keys(raw, _PROJECT_KEYS, f"projects[{index}]")
        local_root = normalize_windows_root(raw["local_root"])
        _project_within_boundary(local_root, boundary)
        projects.append(
            ProjectDefinition(
                project_id=raw["project_id"],
                display_name=raw["display_name"],
                local_root=local_root,
                github=_github(raw["github"], f"projects[{index}].github"),
                supabase=_supabase(raw["supabase"], f"projects[{index}].supabase"),
            )
        )
    return ProjectRegistry(
        default_project_id=str(root["default_project_id"]),
        projects=tuple(projects),
        schema_version=1,
    )


__all__ = ["load_project_registry_settings"]
