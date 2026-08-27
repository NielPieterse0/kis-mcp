from __future__ import annotations

import json
import ntpath
import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

from ...paths import is_within_windows_boundary, normalize_windows_path
from ...projects import load_project_registry_settings
from ...state import (
    StateNamespaceRequest,
    StateNamespaceResolver,
    StateOwnershipClass,
    derive_worktree_source_id,
)

_REVISION = re.compile(r"^[0-9a-f]{40}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ENVIRONMENT = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_KEYS = frozenset(
    {
        "schema_version",
        "enabled",
        "namespace",
        "source_repository",
        "source_revision",
        "package_name",
        "package_version",
        "package_sha256",
        "project_boundary",
        "install_root",
        "executable",
        "arguments",
        "home_root",
        "config_root",
        "cache_root",
        "log_root",
        "temp_root",
        "language_server_root",
        "global_memory_root",
        "project_data_root",
        "project_data_directory",
        "environment_names",
    }
)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _array(
    value: Any,
    label: str,
    *,
    unique: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    values = tuple(_text(item, label) for item in value)
    if unique and len(set(values)) != len(values):
        raise ValueError(f"{label} values must be unique")
    return values


@dataclass(frozen=True, slots=True)
class SerenaSettings:
    enabled: bool
    namespace: str
    source_repository: str
    source_revision: str
    package_name: str
    package_version: str
    package_sha256: str
    project_boundary: str
    install_root: Path
    executable: Path
    arguments: tuple[str, ...]
    home_root: Path
    config_root: Path
    cache_root: Path
    log_root: Path
    temp_root: Path
    language_server_root: Path
    global_memory_root: Path
    project_data_root: Path
    project_data_directory: str
    environment_names: tuple[str, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        if self.namespace != "serena":
            raise ValueError("namespace must be serena")
        if self.source_repository != "https://github.com/oraios/serena":
            raise ValueError("source_repository must identify the official Serena repository")
        if not _REVISION.fullmatch(self.source_revision):
            raise ValueError("source_revision must be a 40-character commit SHA")
        if self.package_name != "serena-agent":
            raise ValueError("package_name must be serena-agent")
        if not _VERSION.fullmatch(self.package_version):
            raise ValueError("package_version must be an exact semantic version")
        if not _SHA256.fullmatch(self.package_sha256):
            raise ValueError("package_sha256 must be a lower-case SHA-256")
        boundary = normalize_windows_path(self.project_boundary, base=self.project_boundary)
        if boundary.casefold() != r"C:\Projects".casefold():
            raise ValueError("project_boundary must be C:\\Projects")
        object.__setattr__(self, "project_boundary", boundary)

        for field_name in (
            "install_root",
            "executable",
            "home_root",
            "config_root",
            "cache_root",
            "log_root",
            "temp_root",
            "language_server_root",
            "global_memory_root",
            "project_data_root",
        ):
            normalized = normalize_windows_path(str(getattr(self, field_name)), base=boundary)
            if not is_within_windows_boundary(normalized, boundary=boundary):
                raise ValueError(f"{field_name} must remain inside project_boundary")
            object.__setattr__(self, field_name, Path(normalized))

        if not is_within_windows_boundary(
            str(self.project_data_root),
            boundary=str(self.install_root),
        ):
            raise ValueError("project_data_root must remain inside install_root")
        if self.project_data_directory != ".serena":
            raise ValueError("project_data_directory must be .serena")
        launcher_prefix = (
            "-c",
            "from serena.cli import top_level; top_level()",
            "start-mcp-server",
        )
        if self.arguments[:3] != launcher_prefix:
            raise ValueError("arguments must launch the pinned Serena CLI through the relocatable venv interpreter")
        required_arguments = {
            "--context=codex",
            "--project-from-cwd",
            "--enable-web-dashboard=false",
            "--open-web-dashboard=false",
            "--enable-gui-log-window=false",
        }
        if not required_arguments.issubset(set(self.arguments)):
            raise ValueError("arguments are missing required fixed Serena flags")
        if any(not _ENVIRONMENT.fullmatch(name) for name in self.environment_names):
            raise ValueError("environment_names must use upper-case shell syntax")
        if len(set(self.environment_names)) != len(self.environment_names):
            raise ValueError("environment_names must be unique")

    @property
    def project_serena_folder_template(self) -> str:
        return ntpath.join(
            str(self.project_data_root),
            "$projectFolderName",
            self.project_data_directory,
        )

    def normalized_project_root(self, project_root: str) -> str:
        normalized_project = normalize_windows_path(
            project_root,
            base=self.project_boundary,
        )
        if not is_within_windows_boundary(
            normalized_project,
            boundary=self.project_boundary,
        ):
            raise ValueError("project_root must remain inside project_boundary")
        folder_name = ntpath.basename(normalized_project.rstrip("\\"))
        if not folder_name:
            raise ValueError("project_root must resolve to a named project folder")
        return normalized_project

    def project_data_path(self, project_root: str) -> Path:
        normalized_project = self.normalized_project_root(project_root)
        folder_name = ntpath.basename(normalized_project.rstrip("\\"))
        project_data = normalize_windows_path(
            ntpath.join(
                str(self.project_data_root),
                folder_name,
                self.project_data_directory,
            ),
            base=str(self.project_data_root),
        )
        if not is_within_windows_boundary(
            project_data,
            boundary=str(self.project_data_root),
        ):
            raise ValueError("project data path must remain inside project_data_root")
        return Path(project_data)

    def project_identity_path(self, project_root: str) -> Path:
        return self.project_data_path(project_root).parent / "project-root.json"

    def canonical_project_identity(self, project_root: str) -> tuple[Path, dict[str, object]]:
        normalized_project = self.normalized_project_root(project_root)
        registry = load_project_registry_settings()
        project = registry.project_for_root(normalized_project)
        source_id = derive_worktree_source_id(normalized_project)
        namespace = StateNamespaceResolver().resolve(
            StateNamespaceRequest(
                ownership=StateOwnershipClass.RECONSTRUCTIBLE_CACHE,
                state_key="serena-project-data",
                identities={"project_id": project.project_id, "source_id": source_id},
            )
        )
        state_root = self.project_data_root.parent.parent
        path = state_root.joinpath(
            *PureWindowsPath(namespace.relative_path).parts,
            "project-root.json",
        )
        return path, {
            "schema_version": 1,
            "project_id": project.project_id,
            "source_id": source_id,
            "project_root": normalized_project,
        }

    @staticmethod
    def _read_identity_marker(path: Path) -> dict[str, object] | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _write_identity_marker(path: Path, expected: dict[str, object]) -> None:
        rendered = json.dumps(expected, indent=2, sort_keys=True) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(rendered)
        except FileExistsError:
            try:
                current = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise ValueError("Serena canonical project identity marker is unreadable") from exc
            if current != rendered:
                raise ValueError("Serena canonical project identity collision")

    def ensure_project_data_path(self, project_root: str) -> Path:
        normalized_project = self.normalized_project_root(project_root)
        project_data = self.project_data_path(normalized_project)
        legacy_identity_path = self.project_identity_path(normalized_project)
        canonical_identity_path, expected = self.canonical_project_identity(normalized_project)
        legacy = self._read_identity_marker(legacy_identity_path)

        if legacy is None and project_data.exists():
            raise ValueError(
                "Serena project state identity is ambiguous: legacy project data exists without "
                "an identity marker"
            )
        if legacy is not None:
            legacy_root = legacy.get("project_root")
            legacy_exact = (
                legacy.get("schema_version") == 1
                and isinstance(legacy_root, str)
                and legacy_root.casefold() == normalized_project.casefold()
            )
            canonical_exact = all(legacy.get(key) == value for key, value in expected.items())
            if not legacy_exact or (
                set(legacy) != {"schema_version", "project_root"} and not canonical_exact
            ):
                raise ValueError(
                    "Serena project state collision: project folder name is already bound "
                    "to a different canonical project/source identity"
                )

        self._write_identity_marker(canonical_identity_path, expected)
        legacy_identity_path.parent.mkdir(parents=True, exist_ok=True)
        if legacy is None:
            self._write_identity_marker(legacy_identity_path, expected)
        project_data.mkdir(parents=True, exist_ok=True)
        return project_data

    @classmethod
    def load(cls, path: Path) -> "SerenaSettings":
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("settings must be a JSON object")
        actual = set(document)
        unknown = sorted(actual - _KEYS)
        if unknown:
            raise ValueError(f"unknown settings keys: {', '.join(unknown)}")
        missing = sorted(_KEYS - actual)
        if missing:
            raise ValueError(f"missing settings keys: {', '.join(missing)}")
        path_fields = {
            name: Path(_text(document[name], name))
            for name in (
                "install_root",
                "executable",
                "home_root",
                "config_root",
                "cache_root",
                "log_root",
                "temp_root",
                "language_server_root",
                "global_memory_root",
                "project_data_root",
            )
        }
        return cls(
            schema_version=document["schema_version"],
            enabled=document["enabled"],
            namespace=_text(document["namespace"], "namespace"),
            source_repository=_text(document["source_repository"], "source_repository"),
            source_revision=_text(document["source_revision"], "source_revision"),
            package_name=_text(document["package_name"], "package_name"),
            package_version=_text(document["package_version"], "package_version"),
            package_sha256=_text(document["package_sha256"], "package_sha256"),
            project_boundary=_text(document["project_boundary"], "project_boundary"),
            arguments=_array(document["arguments"], "arguments"),
            project_data_directory=_text(document["project_data_directory"], "project_data_directory"),
            environment_names=_array(
                document["environment_names"],
                "environment_names",
                unique=True,
            ),
            **path_fields,
        )


__all__ = ["SerenaSettings"]