from __future__ import annotations

import hashlib
import json
import re
import tomllib
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any

from .contracts import (
    Confidence,
    EvidenceItem,
    EvidenceSource,
    Freshness,
    ManifestEvidence,
    ProjectDiagnostic,
    Provenance,
    ProvenanceKind,
    Severity,
    TrustState,
)
from .errors import DiscoverError
from .read_authority import ReadAuthority
from .scanner import RepositorySnapshot, ScannedFile
from .settings import DiscoverSettings

_LANGUAGE_BY_SUFFIX = {
    ".c": "C",
    ".cpp": "C++",
    ".cs": "C#",
    ".go": "Go",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".mjs": "JavaScript",
    ".ps1": "PowerShell",
    ".py": "Python",
    ".rs": "Rust",
    ".sh": "Shell",
    ".sql": "SQL",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
}

_PYTHON_FRAMEWORKS = {
    "django": "Django",
    "fastapi": "FastAPI",
    "fastmcp": "FastMCP",
    "flask": "Flask",
    "pydantic": "Pydantic",
    "pytest": "pytest",
    "sqlalchemy": "SQLAlchemy",
    "starlette": "Starlette",
}
_NODE_FRAMEWORKS = {
    "@nestjs/core": "NestJS",
    "express": "Express",
    "jest": "Jest",
    "next": "Next.js",
    "react": "React",
    "svelte": "Svelte",
    "vitest": "Vitest",
    "vue": "Vue",
}
_BUILD_BACKENDS = {
    "flit_core.buildapi": "Flit",
    "hatchling.build": "Hatchling",
    "maturin": "Maturin",
    "pdm.backend": "PDM",
    "poetry.core.masonry.api": "Poetry",
    "setuptools.build_meta": "Setuptools",
}
_INSTRUCTION_NAMES = {
    "agents.md",
    "claude.md",
    "contributing.md",
    "development.md",
    "gemini.md",
}
_DOCUMENT_NAMES = {
    "architecture.md",
    "governance.md",
    "operations.md",
    "readme.md",
    "security.md",
    "testing.md",
}
_SAFE_ID = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True, slots=True)
class LanguageSummary:
    language: str
    files: int

    def to_json_dict(self) -> dict[str, Any]:
        return {"language": self.language, "files": self.files}


@dataclass(frozen=True, slots=True)
class WorkspaceEvidence:
    pattern: str
    source_path: str

    def to_json_dict(self) -> dict[str, Any]:
        return {"pattern": self.pattern, "source_path": self.source_path}


@dataclass(frozen=True, slots=True)
class EntryPointEvidence:
    name: str
    target: str
    source_path: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "target": self.target,
            "source_path": self.source_path,
        }


@dataclass(frozen=True, slots=True)
class ContractArtifact:
    kind: str
    path: str

    def to_json_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "path": self.path}


@dataclass(frozen=True, slots=True)
class RepositoryDetection:
    project_name: str | None
    languages: tuple[LanguageSummary, ...]
    manifests: tuple[ManifestEvidence, ...]
    frameworks: tuple[str, ...]
    build_systems: tuple[str, ...]
    package_managers: tuple[str, ...]
    workspaces: tuple[WorkspaceEvidence, ...]
    entry_points: tuple[EntryPointEvidence, ...]
    instructions: tuple[str, ...]
    documentation: tuple[str, ...]
    ci: tuple[str, ...]
    contract_artifacts: tuple[ContractArtifact, ...]
    modules: tuple[str, ...]
    evidence: tuple[EvidenceItem, ...]
    diagnostics: tuple[ProjectDiagnostic, ...]
    unknowns: tuple[str, ...]

    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json_value(getattr(self, field.name)) for field in fields(self)}


class RepositoryDetector:
    def __init__(self, authority: ReadAuthority, settings: DiscoverSettings) -> None:
        self._authority = authority
        self._settings = settings

    def detect(
        self,
        project_path: str,
        snapshot: RepositorySnapshot,
    ) -> RepositoryDetection:
        by_path = {record.label: record for record in snapshot.files}
        language_counts = Counter(
            language
            for record in snapshot.files
            if _manifest_descriptor(record.label) is None
            and record.category in {"source", "test"}
            and (language := _LANGUAGE_BY_SUFFIX.get(record.suffix)) is not None
        )
        frameworks: set[str] = set()
        build_systems: set[str] = set()
        package_managers = _package_managers_from_paths(by_path)
        workspaces: list[WorkspaceEvidence] = []
        entry_points: list[EntryPointEvidence] = []
        manifests: list[ManifestEvidence] = []
        diagnostics: list[ProjectDiagnostic] = []
        evidence: list[EvidenceItem] = []
        project_name: str | None = None

        manifest_records = [
            record for record in snapshot.files if _manifest_descriptor(record.label) is not None
        ]
        manifest_records.sort(
            key=lambda item: (_manifest_priority(item.label), item.label.casefold())
        )
        for record in manifest_records:
            descriptor = _manifest_descriptor(record.label)
            assert descriptor is not None
            kind, ecosystem, manager, workspace = descriptor
            resolved_manager = manager or _manager_for_manifest(record.label, package_managers)
            try:
                text = self._authority.read_relative_text(
                    project_path,
                    record.label,
                    max_bytes=self._settings.limits.max_file_bytes,
                ).content
                name = PurePosixPath(record.label).name.casefold()
                if name == "pyproject.toml":
                    data = tomllib.loads(text)
                    detected_name = _inspect_pyproject(
                        data,
                        record.label,
                        frameworks,
                        build_systems,
                        entry_points,
                    )
                    if project_name is None and _is_root(record.label):
                        project_name = detected_name
                elif name == "package.json":
                    data = json.loads(text)
                    if not isinstance(data, dict):
                        raise ValueError("package.json root must be an object")
                    detected_name, package_manager = _inspect_package_json(
                        data,
                        record.label,
                        frameworks,
                        workspaces,
                    )
                    if package_manager:
                        package_managers.add(package_manager)
                        resolved_manager = package_manager
                    workspace = bool(workspaces)
                    if project_name is None and _is_root(record.label):
                        project_name = detected_name
                elif name in {"cargo.toml"}:
                    tomllib.loads(text)
                elif name.endswith((".csproj", ".fsproj", ".vbproj")):
                    if "<project" not in text.casefold():
                        raise ValueError("project file root is missing")
                elif name == "pom.xml":
                    if "<project" not in text.casefold():
                        raise ValueError("Maven project root is missing")
            except (DiscoverError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError, UnicodeError) as exc:
                diagnostics.append(
                    ProjectDiagnostic(
                        code="MANIFEST_PARSE_FAILED",
                        message=f"Manifest evidence could not be parsed: {type(exc).__name__}.",
                        severity=Severity.WARNING,
                        path=record.label,
                    )
                )

            _add_build_and_manager_evidence(
                record.label,
                build_systems,
                package_managers,
            )
            manifest = ManifestEvidence(
                path=record.label,
                kind=kind,
                ecosystem=ecosystem,
                package_manager=resolved_manager,
                workspace=workspace,
                confidence=Confidence.HIGH,
                evidence_ids=(_evidence_id("manifest", record.label),),
            )
            manifests.append(manifest)
            evidence.append(
                _evidence(
                    snapshot,
                    kind="manifest",
                    path=record.label,
                    summary=f"Detected {kind.replace('_', ' ')} manifest.",
                    details={
                        "ecosystem": ecosystem,
                        "package_manager": resolved_manager,
                        "workspace": workspace,
                    },
                    provenance=ProvenanceKind.DECLARED,
                )
            )

        instructions = tuple(
            sorted(
                (
                    record.label
                    for record in snapshot.files
                    if _is_instruction(record.label)
                ),
                key=str.casefold,
            )
        )
        documentation = tuple(
            sorted(
                (
                    record.label
                    for record in snapshot.files
                    if _is_documentation(record.label)
                    and record.label not in instructions
                ),
                key=str.casefold,
            )
        )
        ci = tuple(
            sorted(
                (
                    record.label
                    for record in snapshot.files
                    if record.label.casefold().startswith(".github/workflows/")
                    and record.suffix in {".yml", ".yaml"}
                ),
                key=str.casefold,
            )
        )
        contract_artifacts = tuple(
            sorted(
                (
                    artifact
                    for record in snapshot.files
                    if (artifact := _contract_artifact(record.label)) is not None
                ),
                key=lambda item: (item.kind, item.path.casefold()),
            )
        )
        modules = _major_modules(snapshot.files)

        languages = tuple(
            LanguageSummary(language=language, files=count)
            for language, count in sorted(
                language_counts.items(), key=lambda item: (-item[1], item[0].casefold())
            )
        )
        for language in languages:
            evidence.append(
                _evidence(
                    snapshot,
                    kind="language",
                    path=".",
                    summary=f"Detected {language.language} source files.",
                    details=language.to_json_dict(),
                    provenance=ProvenanceKind.OBSERVED,
                )
            )
        for path in instructions:
            evidence.append(
                _evidence(
                    snapshot,
                    kind="instruction",
                    path=path,
                    summary="Detected repository instruction file.",
                    details={},
                    provenance=ProvenanceKind.DECLARED,
                )
            )
        for path in documentation:
            evidence.append(
                _evidence(
                    snapshot,
                    kind="documentation",
                    path=path,
                    summary="Detected canonical repository documentation.",
                    details={},
                    provenance=ProvenanceKind.OBSERVED,
                )
            )
        for path in ci:
            evidence.append(
                _evidence(
                    snapshot,
                    kind="ci",
                    path=path,
                    summary="Detected local CI workflow.",
                    details={"provider": "GitHub Actions"},
                    provenance=ProvenanceKind.DECLARED,
                )
            )
        for artifact in contract_artifacts:
            evidence.append(
                _evidence(
                    snapshot,
                    kind="contract",
                    path=artifact.path,
                    summary=f"Detected {artifact.kind.replace('_', ' ')} contract artifact.",
                    details={"contract_kind": artifact.kind},
                    provenance=ProvenanceKind.DECLARED,
                )
            )

        unknowns: list[str] = []
        if not languages:
            unknowns.append("No supported source-language files were detected within scan bounds.")
        if not manifests:
            unknowns.append("No supported project manifest was detected.")
        if snapshot.truncated:
            unknowns.append("Repository scan was truncated by configured or filesystem safety limits.")

        diagnostics.sort(key=lambda item: (item.code, (item.path or "").casefold()))
        evidence.sort(key=lambda item: item.id)
        return RepositoryDetection(
            project_name=project_name,
            languages=languages,
            manifests=tuple(manifests),
            frameworks=tuple(sorted(frameworks, key=str.casefold)),
            build_systems=tuple(sorted(build_systems, key=str.casefold)),
            package_managers=tuple(sorted(package_managers, key=str.casefold)),
            workspaces=tuple(sorted(workspaces, key=lambda item: (item.source_path.casefold(), item.pattern.casefold()))),
            entry_points=tuple(sorted(entry_points, key=lambda item: (item.source_path.casefold(), item.name.casefold()))),
            instructions=instructions,
            documentation=documentation,
            ci=ci,
            contract_artifacts=contract_artifacts,
            modules=modules,
            evidence=tuple(evidence),
            diagnostics=tuple(diagnostics),
            unknowns=tuple(unknowns),
        )


def _inspect_pyproject(
    data: Mapping[str, Any],
    source: str,
    frameworks: set[str],
    build_systems: set[str],
    entry_points: list[EntryPointEvidence],
) -> str | None:
    project = data.get("project")
    dependencies: set[str] = set()
    project_name: str | None = None
    if isinstance(project, Mapping):
        name = project.get("name")
        if isinstance(name, str) and name.strip():
            project_name = name
        values = project.get("dependencies")
        if isinstance(values, list):
            dependencies.update(
                _dependency_name(value) for value in values if isinstance(value, str)
            )
        optional = project.get("optional-dependencies")
        if isinstance(optional, Mapping):
            for group in optional.values():
                if isinstance(group, list):
                    dependencies.update(
                        _dependency_name(value) for value in group if isinstance(value, str)
                    )
        for table_name in ("scripts", "gui-scripts"):
            scripts = project.get(table_name)
            if isinstance(scripts, Mapping):
                for name, target in scripts.items():
                    if isinstance(name, str) and isinstance(target, str):
                        entry_points.append(
                            EntryPointEvidence(
                                name=name,
                                target=target,
                                source_path=source,
                            )
                        )

    dependency_groups = data.get("dependency-groups")
    if isinstance(dependency_groups, Mapping):
        for group in dependency_groups.values():
            if isinstance(group, list):
                dependencies.update(
                    _dependency_name(value) for value in group if isinstance(value, str)
                )

    tool = data.get("tool")
    if isinstance(tool, Mapping):
        poetry = tool.get("poetry")
        if isinstance(poetry, Mapping):
            poetry_dependencies = poetry.get("dependencies")
            if isinstance(poetry_dependencies, Mapping):
                dependencies.update(
                    str(value).casefold().replace("_", "-")
                    for value in poetry_dependencies
                )
        if "pytest" in tool:
            frameworks.add("pytest")

    for dependency, display in _PYTHON_FRAMEWORKS.items():
        if dependency in dependencies:
            frameworks.add(display)

    build_system = data.get("build-system")
    if isinstance(build_system, Mapping):
        backend = build_system.get("build-backend")
        if isinstance(backend, str):
            display = next(
                (
                    name
                    for prefix, name in _BUILD_BACKENDS.items()
                    if backend.startswith(prefix)
                ),
                backend,
            )
            build_systems.add(display)
    return project_name


def _inspect_package_json(
    data: Mapping[str, Any],
    source: str,
    frameworks: set[str],
    workspaces: list[WorkspaceEvidence],
) -> tuple[str | None, str | None]:
    dependencies: dict[str, Any] = {}
    for key in (
        "dependencies",
        "devDependencies",
        "optionalDependencies",
        "peerDependencies",
    ):
        values = data.get(key)
        if isinstance(values, Mapping):
            dependencies.update({str(name): value for name, value in values.items()})
    for dependency, display in _NODE_FRAMEWORKS.items():
        if dependency in dependencies:
            frameworks.add(display)

    raw_workspaces = data.get("workspaces")
    patterns: list[str] = []
    if isinstance(raw_workspaces, list):
        patterns = [value for value in raw_workspaces if isinstance(value, str)]
    elif isinstance(raw_workspaces, Mapping):
        packages = raw_workspaces.get("packages")
        if isinstance(packages, list):
            patterns = [value for value in packages if isinstance(value, str)]
    workspaces.extend(
        WorkspaceEvidence(pattern=pattern, source_path=source) for pattern in patterns
    )

    package_manager: str | None = None
    raw_manager = data.get("packageManager")
    if isinstance(raw_manager, str) and raw_manager.strip():
        package_manager = raw_manager.split("@", 1)[0].casefold()
    name = data.get("name")
    return (name if isinstance(name, str) else None, package_manager)


def _manifest_priority(label: str) -> tuple[int, int]:
    path = PurePosixPath(label)
    name = path.name.casefold()
    root_priority = 0 if len(path.parts) == 1 else 1
    authority_priority = {
        "pyproject.toml": 0,
        "package.json": 1,
        "cargo.toml": 2,
        "go.mod": 3,
        "pom.xml": 4,
    }.get(name, 10)
    return (root_priority, authority_priority)


def _manifest_descriptor(label: str) -> tuple[str, str, str | None, bool] | None:
    name = PurePosixPath(label).name.casefold()
    suffix = PurePosixPath(label).suffix.casefold()
    exact = {
        "build.gradle": ("gradle_project", "jvm", "Gradle", False),
        "build.gradle.kts": ("gradle_project", "jvm", "Gradle", False),
        "cargo.toml": ("rust_package", "rust", "Cargo", False),
        "cmakelists.txt": ("cmake_project", "native", None, False),
        "dockerfile": ("container_build", "container", None, False),
        "go.mod": ("go_module", "go", "Go modules", False),
        "makefile": ("make_project", "native", None, False),
        "package.json": ("node_package", "node", None, False),
        "pipfile": ("python_dependencies", "python", "Pipenv", False),
        "pom.xml": ("maven_project", "jvm", "Maven", False),
        "pyproject.toml": ("python_project", "python", None, False),
        "requirements.txt": ("python_dependencies", "python", "pip", False),
    }
    if name in exact:
        return exact[name]
    if suffix in {".csproj", ".fsproj", ".vbproj"}:
        return ("dotnet_project", "dotnet", "dotnet", False)
    if suffix in {".sln", ".slnx"}:
        return ("dotnet_solution", "dotnet", "dotnet", True)
    return None


def _package_managers_from_paths(by_path: Mapping[str, ScannedFile]) -> set[str]:
    managers: set[str] = set()
    names = {PurePosixPath(path).name.casefold() for path in by_path}
    for name, manager in (
        ("cargo.lock", "Cargo"),
        ("package-lock.json", "npm"),
        ("pipfile.lock", "Pipenv"),
        ("pnpm-lock.yaml", "pnpm"),
        ("poetry.lock", "Poetry"),
        ("uv.lock", "uv"),
        ("yarn.lock", "Yarn"),
    ):
        if name in names:
            managers.add(manager)
    return managers


def _manager_for_manifest(label: str, managers: set[str]) -> str | None:
    name = PurePosixPath(label).name.casefold()
    if name == "pyproject.toml":
        for candidate in ("uv", "Poetry", "Pipenv", "pip"):
            if candidate in managers:
                return candidate
    if name == "package.json":
        for candidate in ("pnpm", "Yarn", "npm"):
            if candidate in managers:
                return candidate
    return None


def _add_build_and_manager_evidence(
    label: str,
    build_systems: set[str],
    package_managers: set[str],
) -> None:
    name = PurePosixPath(label).name.casefold()
    suffix = PurePosixPath(label).suffix.casefold()
    if name == "cargo.toml":
        build_systems.add("Cargo")
        package_managers.add("Cargo")
    elif name == "go.mod":
        build_systems.add("Go modules")
        package_managers.add("Go modules")
    elif name == "pom.xml":
        build_systems.add("Maven")
        package_managers.add("Maven")
    elif name in {"build.gradle", "build.gradle.kts"}:
        build_systems.add("Gradle")
        package_managers.add("Gradle")
    elif suffix in {".csproj", ".fsproj", ".vbproj", ".sln", ".slnx"}:
        build_systems.add(".NET/MSBuild")
        package_managers.add("dotnet")
    elif name == "cmakelists.txt":
        build_systems.add("CMake")
    elif name == "makefile":
        build_systems.add("Make")
    elif name == "dockerfile":
        build_systems.add("Docker")


def _is_instruction(label: str) -> bool:
    normalized = label.casefold()
    name = PurePosixPath(label).name.casefold()
    return name in _INSTRUCTION_NAMES or normalized == ".github/copilot-instructions.md"


def _is_documentation(label: str) -> bool:
    path = PurePosixPath(label)
    name = path.name.casefold()
    parts = {part.casefold() for part in path.parts[:-1]}
    return name in _DOCUMENT_NAMES or (
        "docs" in parts and path.suffix.casefold() == ".md"
    )


def _contract_artifact(label: str) -> ContractArtifact | None:
    path = PurePosixPath(label)
    normalized = label.casefold()
    name = path.name.casefold()
    suffix = path.suffix.casefold()
    if name.startswith(("openapi.", "swagger.")) and suffix in {".json", ".yaml", ".yml"}:
        return ContractArtifact(kind="openapi", path=label)
    if name.startswith("asyncapi.") and suffix in {".json", ".yaml", ".yml"}:
        return ContractArtifact(kind="asyncapi", path=label)
    if suffix == ".json" and (".schema." in name or name.endswith("schema.json")):
        return ContractArtifact(kind="json_schema", path=label)
    if suffix in {".graphql", ".graphqls", ".gql"}:
        return ContractArtifact(kind="graphql", path=label)
    if suffix == ".proto":
        return ContractArtifact(kind="protobuf", path=label)
    if suffix == ".sql" and any(
        segment in {"database", "db", "migrations", "schema"}
        for segment in normalized.split("/")[:-1]
    ):
        return ContractArtifact(kind="database", path=label)
    return None


def _major_modules(files: tuple[ScannedFile, ...]) -> tuple[str, ...]:
    modules: set[str] = set()
    for record in files:
        if record.category != "source":
            continue
        parts = PurePosixPath(record.label).parts
        if len(parts) >= 3 and parts[0].casefold() in {
            "app",
            "apps",
            "lib",
            "packages",
            "src",
        }:
            modules.add(f"{parts[0]}/{parts[1]}")
        elif len(parts) >= 2 and parts[0].casefold() not in {
            "docs",
            "scripts",
            "test",
            "tests",
        }:
            modules.add(parts[0])
    return tuple(sorted(modules, key=str.casefold))


def _evidence(
    snapshot: RepositorySnapshot,
    *,
    kind: str,
    path: str,
    summary: str,
    details: Mapping[str, Any],
    provenance: ProvenanceKind,
) -> EvidenceItem:
    evidence_id = _evidence_id(kind, path if path != "." else summary)
    return EvidenceItem(
        id=evidence_id,
        kind=kind,
        subject=snapshot.project.project_id,
        source=EvidenceSource(
            kind="file" if path != "." else "repository",
            provider="local_filesystem",
            identifier=path,
        ),
        provenance=Provenance(kind=provenance, source_id=path),
        location={"path": path},
        trust=TrustState.TRUSTED,
        confidence=Confidence.HIGH,
        freshness=Freshness.CURRENT,
        summary=summary,
        details=details,
        truncated=False,
    )


def _evidence_id(kind: str, value: str) -> str:
    slug = _SAFE_ID.sub("-", value.casefold()).strip("-") or "root"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return f"ev-{kind}-{slug}-{digest}"


def _dependency_name(value: str) -> str:
    lowered = value.strip().casefold()
    for separator in ("[", " ", "<", ">", "=", "!", "~", ";"):
        lowered = lowered.split(separator, 1)[0]
    return lowered.replace("_", "-")


def _is_root(label: str) -> bool:
    return len(PurePosixPath(label).parts) == 1


def _json_value(value: Any) -> Any:
    if hasattr(value, "to_json_dict"):
        return value.to_json_dict()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"value is not JSON-compatible: {type(value).__name__}")


__all__ = [
    "ContractArtifact",
    "EntryPointEvidence",
    "LanguageSummary",
    "RepositoryDetection",
    "RepositoryDetector",
    "WorkspaceEvidence",
]
