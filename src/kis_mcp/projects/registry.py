from __future__ import annotations

from dataclasses import dataclass

from .contracts import ProjectDefinition, normalize_windows_root


@dataclass(frozen=True, slots=True)
class ProjectRegistry:
    default_project_id: str
    projects: tuple[ProjectDefinition, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("project registry schema_version must be 1")
        projects = tuple(sorted(self.projects, key=lambda item: item.project_id))
        if not projects:
            raise ValueError("project registry must contain at least one project")
        project_ids = [item.project_id for item in projects]
        if len(set(project_ids)) != len(project_ids):
            raise ValueError("project registry project_id values must be unique")
        roots = [item.local_root.casefold() for item in projects]
        if len(set(roots)) != len(roots):
            raise ValueError("project registry local_root values must be unique")
        if self.default_project_id not in set(project_ids):
            raise ValueError("default_project_id must identify a registered project")
        object.__setattr__(self, "projects", projects)

        repositories = [
            item.github.repository
            for item in projects
            if item.github is not None
        ]
        if len(set(repositories)) != len(repositories):
            raise ValueError("duplicate GitHub repository in project registry")
        project_coordinates = [
            (resource.owner.casefold(), resource.owner_type, resource.project_number)
            for item in projects
            if item.github is not None
            for resource in item.github.projects
        ]
        if len(set(project_coordinates)) != len(project_coordinates):
            raise ValueError("duplicate GitHub Project in project registry")
        supabase_refs = [
            item.supabase.project_ref
            for item in projects
            if item.supabase is not None
        ]
        if len(set(supabase_refs)) != len(supabase_refs):
            raise ValueError("duplicate Supabase project_ref in project registry")

    @property
    def default_project(self) -> ProjectDefinition:
        return self.project(self.default_project_id)

    def project(self, project_id: str) -> ProjectDefinition:
        for project in self.projects:
            if project.project_id == project_id:
                return project
        raise KeyError(f"unknown project_id: {project_id}")

    def project_for_root(self, local_root: str) -> ProjectDefinition:
        target = normalize_windows_root(local_root).casefold()
        matches = [
            project
            for project in self.projects
            if target == project.local_root.casefold()
            or target.startswith(project.local_root.casefold().rstrip("\\") + "\\")
        ]
        if matches:
            return max(matches, key=lambda project: len(project.local_root))
        raise KeyError(f"Unregistered project root: {local_root}")

    @property
    def github_repositories(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                project.github.repository
                for project in self.projects
                if project.github is not None
            )
        )

    @property
    def github_project_coordinates(self) -> tuple[tuple[str, str, int], ...]:
        return tuple(
            sorted(
                (resource.owner, resource.owner_type, resource.project_number)
                for project in self.projects
                if project.github is not None
                for resource in project.github.projects
            )
        )

    @property
    def supabase_project_refs(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                project.supabase.project_ref
                for project in self.projects
                if project.supabase is not None
            )
        )

    def to_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "default_project_id": self.default_project_id,
            "projects": [project.to_json_dict() for project in self.projects],
        }


__all__ = ["ProjectRegistry"]
