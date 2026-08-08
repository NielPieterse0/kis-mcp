from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Any

_PROJECT_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_GITHUB_PART = re.compile(r"^[A-Za-z0-9_.-]+$")
_SUPABASE_PROJECT_REF = re.compile(r"^[a-z0-9]{20}$")


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _kebab(value: Any, label: str) -> str:
    normalized = _required_text(value, label)
    if _PROJECT_ID.fullmatch(normalized) is None:
        raise ValueError(f"{label} must use lower-case kebab-case")
    return normalized


def normalize_windows_root(value: Any, label: str = "local_root") -> str:
    raw = _required_text(value, label)
    path = PureWindowsPath(raw)
    if not path.is_absolute() or path.drive == "":
        raise ValueError(f"{label} must be an absolute Windows path")
    if ".." in path.parts:
        raise ValueError(f"{label} must not contain parent traversal")
    return str(path)


def normalize_github_repository(value: Any) -> str:
    raw = _required_text(value, "github.repository")
    if raw.count("/") != 1 or any(char.isspace() for char in raw):
        raise ValueError("github.repository must use owner/name")
    owner, name = raw.split("/", 1)
    if not owner or not name:
        raise ValueError("github.repository must use owner/name")
    if _GITHUB_PART.fullmatch(owner) is None or _GITHUB_PART.fullmatch(name) is None:
        raise ValueError("github.repository contains unsupported characters")
    return f"{owner.casefold()}/{name.casefold()}"


@dataclass(frozen=True, slots=True)
class GitHubProjectResource:
    binding_id: str
    owner: str
    owner_type: str
    project_number: int

    def __post_init__(self) -> None:
        binding_id = _kebab(self.binding_id, "github.projects.binding_id")
        owner = _required_text(self.owner, "github.projects.owner")
        owner_type = _required_text(self.owner_type, "github.projects.owner_type").casefold()
        if owner_type not in {"user", "org"}:
            raise ValueError("github.projects.owner_type must be user or org")
        if isinstance(self.project_number, bool) or not isinstance(self.project_number, int):
            raise ValueError("github.projects.project_number must be a positive integer")
        if self.project_number <= 0:
            raise ValueError("github.projects.project_number must be a positive integer")
        object.__setattr__(self, "binding_id", binding_id)
        object.__setattr__(self, "owner", owner)
        object.__setattr__(self, "owner_type", owner_type)

    def to_json_dict(self) -> dict[str, object]:
        return {
            "binding_id": self.binding_id,
            "owner": self.owner,
            "owner_type": self.owner_type,
            "project_number": self.project_number,
        }


@dataclass(frozen=True, slots=True)
class GitHubProjectBinding:
    repository: str
    projects: tuple[GitHubProjectResource, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "repository", normalize_github_repository(self.repository))
        projects = tuple(sorted(self.projects, key=lambda item: item.binding_id))
        binding_ids = [item.binding_id for item in projects]
        if len(set(binding_ids)) != len(binding_ids):
            raise ValueError("github.projects binding_id values must be unique")
        object.__setattr__(self, "projects", projects)

    def to_json_dict(self) -> dict[str, object]:
        return {
            "repository": self.repository,
            "projects": [item.to_json_dict() for item in self.projects],
        }


@dataclass(frozen=True, slots=True)
class SupabaseProjectBinding:
    project_ref: str

    def __post_init__(self) -> None:
        project_ref = _required_text(self.project_ref, "supabase.project_ref")
        if _SUPABASE_PROJECT_REF.fullmatch(project_ref) is None:
            raise ValueError("supabase.project_ref must be 20 lower-case letters or digits")
        object.__setattr__(self, "project_ref", project_ref)

    def to_json_dict(self) -> dict[str, str]:
        return {"project_ref": self.project_ref}


@dataclass(frozen=True, slots=True)
class ProjectDefinition:
    project_id: str
    display_name: str
    local_root: str
    github: GitHubProjectBinding | None = None
    supabase: SupabaseProjectBinding | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _kebab(self.project_id, "project_id"))
        object.__setattr__(self, "display_name", _required_text(self.display_name, "display_name"))
        object.__setattr__(self, "local_root", normalize_windows_root(self.local_root))

    def to_json_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "display_name": self.display_name,
            "local_root": self.local_root,
            "github": None if self.github is None else self.github.to_json_dict(),
            "supabase": None if self.supabase is None else self.supabase.to_json_dict(),
        }


__all__ = [
    "GitHubProjectBinding",
    "GitHubProjectResource",
    "ProjectDefinition",
    "SupabaseProjectBinding",
    "normalize_github_repository",
    "normalize_windows_root",
]
