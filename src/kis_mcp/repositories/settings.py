from __future__ import annotations

import configparser
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


_SETTINGS_KEYS = {
    "schema_version",
    "repository_id",
    "github_repository",
    "gh_projects",
}
_PROJECT_KEYS = {"binding_id", "owner", "owner_type", "project_number"}
_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_GITHUB_PART = re.compile(r"^[A-Za-z0-9_.-]+$")


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{label} must be a non-empty string")
    return value.strip()


def _github_parts(owner: str, repository: str) -> str:
    owner = owner.strip()
    repository = repository.strip()
    if repository.casefold().endswith(".git"):
        repository = repository[:-4]
    if (
        not owner
        or not repository
        or owner in {".", ".."}
        or repository in {".", ".."}
        or _GITHUB_PART.fullmatch(owner) is None
        or _GITHUB_PART.fullmatch(repository) is None
    ):
        raise RuntimeError("github_repository must use owner/repository")
    return f"{owner.casefold()}/{repository.casefold()}"


def normalize_github_repository(value: Any) -> str:
    raw = _required_text(value, "github_repository")
    ssh = re.fullmatch(r"git@github\.com:([^/]+)/([^/]+)", raw, re.IGNORECASE)
    if ssh:
        return _github_parts(ssh.group(1), ssh.group(2))
    if "://" in raw:
        parsed = urlsplit(raw)
        if parsed.username or parsed.password:
            raise RuntimeError("credential-bearing GitHub repository URLs are not accepted")
        parts = [part for part in parsed.path.split("/") if part]
        host = (parsed.hostname or "").casefold()
        if host == "github.com" and len(parts) == 2:
            return _github_parts(parts[0], parts[1])
        if host == "api.github.com" and len(parts) == 3 and parts[0].casefold() == "repos":
            return _github_parts(parts[1], parts[2])
        raise RuntimeError("github_repository must identify github.com owner/repository")
    parts = raw.split("/")
    if len(parts) != 2:
        raise RuntimeError("github_repository must use owner/repository")
    return _github_parts(parts[0], parts[1])


@dataclass(frozen=True, slots=True)
class GitHubProjectBinding:
    binding_id: str
    owner: str
    owner_type: str
    project_number: int

    def __post_init__(self) -> None:
        binding_id = _required_text(self.binding_id, "gh_projects[].binding_id").casefold()
        if _ID.fullmatch(binding_id) is None:
            raise RuntimeError("gh_projects[].binding_id must use lower-case kebab-case")
        owner = _required_text(self.owner, "gh_projects[].owner")
        if _GITHUB_PART.fullmatch(owner) is None or owner in {".", ".."}:
            raise RuntimeError("gh_projects[].owner is invalid")
        owner_type = _required_text(
            self.owner_type, "gh_projects[].owner_type"
        ).casefold()
        if owner_type not in {"user", "org"}:
            raise RuntimeError("gh_projects[].owner_type must be user or org")
        if (
            isinstance(self.project_number, bool)
            or not isinstance(self.project_number, int)
            or self.project_number <= 0
        ):
            raise RuntimeError("gh_projects[].project_number must be a positive integer")
        object.__setattr__(self, "binding_id", binding_id)
        object.__setattr__(self, "owner", owner)
        object.__setattr__(self, "owner_type", owner_type)

    def to_json_dict(self) -> dict[str, str | int]:
        return {
            "binding_id": self.binding_id,
            "owner": self.owner,
            "owner_type": self.owner_type,
            "project_number": self.project_number,
        }


@dataclass(frozen=True, slots=True)
class RepositorySettings:
    repository_root: Path
    repository_id: str
    github_repository: str
    gh_projects: tuple[GitHubProjectBinding, ...]
    schema_version: int = 1

    @property
    def github_owner(self) -> str:
        return self.github_repository.split("/", 1)[0]

    @property
    def github_name(self) -> str:
        return self.github_repository.split("/", 1)[1]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repository_root": str(self.repository_root),
            "repository_id": self.repository_id,
            "github_repository": self.github_repository,
            "gh_projects": [project.to_json_dict() for project in self.gh_projects],
        }


def _load_document(path: Path) -> Mapping[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Repository settings are missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(document, Mapping):
        raise RuntimeError("Repository settings root must be an object")
    return document


def _git_config_path(repository_root: Path) -> Path | None:
    marker = repository_root / ".git"
    if marker.is_dir():
        return marker / "config"
    if not marker.is_file():
        return None
    text = marker.read_text(encoding="utf-8").strip()
    if not text.casefold().startswith("gitdir:"):
        raise RuntimeError(f"Unsupported .git marker: {marker}")
    raw_gitdir = text.split(":", 1)[1].strip()
    gitdir = Path(raw_gitdir)
    if not gitdir.is_absolute():
        gitdir = (repository_root / gitdir).resolve()
    commondir_file = gitdir / "commondir"
    if commondir_file.is_file():
        raw_common = commondir_file.read_text(encoding="utf-8").strip()
        common = Path(raw_common)
        if not common.is_absolute():
            common = (gitdir / common).resolve()
        return common / "config"
    return gitdir / "config"


def _origin_repository(repository_root: Path) -> str | None:
    config_path = _git_config_path(repository_root)
    if config_path is None or not config_path.is_file():
        return None
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(config_path, encoding="utf-8")
    section = 'remote "origin"'
    if not parser.has_option(section, "url"):
        return None
    return normalize_github_repository(parser.get(section, "url"))


def _bounded_root(repository_root: Path, boundary: Path | None) -> Path:
    root = repository_root.resolve()
    if boundary is None:
        return root
    approved = boundary.resolve()
    try:
        root.relative_to(approved)
    except ValueError as exc:
        raise RuntimeError(
            f"Repository root must remain beneath the approved boundary: {approved}"
        ) from exc
    return root


def load_repository_settings(
    repository_root: Path | None = None,
    *,
    validate_remote: bool = True,
) -> RepositorySettings:
    root = (repository_root or Path(__file__).resolve().parents[3]).resolve()
    document = _load_document(root / "settings" / "kis-repository.settings.json")
    unknown = sorted(set(document).difference(_SETTINGS_KEYS))
    missing = sorted(_SETTINGS_KEYS.difference(document))
    if unknown:
        raise RuntimeError(f"Repository settings contain unknown keys: {unknown}")
    if missing:
        raise RuntimeError(f"Repository settings are missing keys: {missing}")
    if document.get("schema_version") != 1:
        raise RuntimeError("Repository settings schema_version must be 1")

    repository_id = _required_text(document.get("repository_id"), "repository_id").casefold()
    if _ID.fullmatch(repository_id) is None:
        raise RuntimeError("repository_id must use lower-case kebab-case")
    github_repository = normalize_github_repository(document.get("github_repository"))

    raw_projects = document.get("gh_projects")
    if not isinstance(raw_projects, Sequence) or isinstance(raw_projects, (str, bytes)):
        raise RuntimeError("gh_projects must be an array")
    projects: list[GitHubProjectBinding] = []
    for raw_project in raw_projects:
        if not isinstance(raw_project, Mapping):
            raise RuntimeError("gh_projects[] must be an object")
        unknown_project_keys = sorted(set(raw_project).difference(_PROJECT_KEYS))
        missing_project_keys = sorted(_PROJECT_KEYS.difference(raw_project))
        if unknown_project_keys:
            raise RuntimeError(
                f"gh_projects[] contains unknown keys: {unknown_project_keys}"
            )
        if missing_project_keys:
            raise RuntimeError(
                f"gh_projects[] is missing keys: {missing_project_keys}"
            )
        projects.append(
            GitHubProjectBinding(
                binding_id=raw_project.get("binding_id"),
                owner=raw_project.get("owner"),
                owner_type=raw_project.get("owner_type"),
                project_number=raw_project.get("project_number"),
            )
        )
    binding_ids = [project.binding_id for project in projects]
    if len(set(binding_ids)) != len(binding_ids):
        raise RuntimeError("gh_projects contains duplicate binding_id values")
    project_keys = [
        (project.owner.casefold(), project.owner_type, project.project_number)
        for project in projects
    ]
    if len(set(project_keys)) != len(project_keys):
        raise RuntimeError("gh_projects contains duplicate project identities")

    if validate_remote:
        origin = _origin_repository(root)
        if origin is not None and origin != github_repository:
            raise RuntimeError(
                "Configured github_repository does not match origin: "
                f"{github_repository} != {origin}"
            )

    return RepositorySettings(
        repository_root=root,
        repository_id=repository_id,
        github_repository=github_repository,
        gh_projects=tuple(projects),
    )


class SelectedRepositorySettings:
    """Mutable repository selection independent from provider client lifetime."""

    def __init__(
        self,
        repository_root: Path | None = None,
        *,
        validate_remote: bool = True,
        boundary: Path | None = None,
    ) -> None:
        self._validate_remote = validate_remote
        self._boundary = boundary.resolve() if boundary is not None else None
        root = repository_root or Path(__file__).resolve().parents[3]
        self._repository_root = root.resolve()
        self._settings: RepositorySettings | None = None

    def current(self) -> RepositorySettings:
        if self._settings is None:
            self._settings = load_repository_settings(
                _bounded_root(self._repository_root, self._boundary),
                validate_remote=self._validate_remote,
            )
        return self._settings

    def select(self, repository_root: Path) -> RepositorySettings:
        root = _bounded_root(repository_root, self._boundary)
        selected = load_repository_settings(
            root,
            validate_remote=self._validate_remote,
        )
        self._repository_root = root
        self._settings = selected
        return selected


__all__ = [
    "GitHubProjectBinding",
    "RepositorySettings",
    "SelectedRepositorySettings",
    "load_repository_settings",
    "normalize_github_repository",
]
