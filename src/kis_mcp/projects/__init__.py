from .contracts import (
    GitHubProjectBinding,
    GitHubProjectResource,
    ProjectDefinition,
    SupabaseProjectBinding,
    normalize_github_repository,
    normalize_windows_root,
)
from .registry import ProjectRegistry
from .settings import load_project_registry_settings

__all__ = [
    "GitHubProjectBinding",
    "GitHubProjectResource",
    "ProjectDefinition",
    "ProjectRegistry",
    "SupabaseProjectBinding",
    "load_project_registry_settings",
    "normalize_github_repository",
    "normalize_windows_root",
]
