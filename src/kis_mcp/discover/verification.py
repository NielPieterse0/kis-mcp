from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any

from .contracts import (
    Confidence,
    ProjectDiagnostic,
    ProvenanceKind,
    Severity,
    VerificationDeclaration,
)
from .errors import DiscoverError
from .read_authority import ReadAuthority
from .scanner import RepositorySnapshot
from .settings import DiscoverSettings

_SAFE_ID = re.compile(r"[^a-z0-9]+")
_SCRIPT_CATEGORY = {
    "build": "build",
    "docs": "documentation",
    "lint": "lint",
    "release": "release",
    "test": "test",
    "test:e2e": "test",
    "test:unit": "test",
    "typecheck": "typecheck",
    "verify": "repository_verification",
}
_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_QUALITY_TOOL_SPECS = {
    "coverage": {
        "packages": ("pytest-cov", "coverage"),
        "default_package": "coverage",
        "config": "coverage",
        "role": "coverage",
        "verification_id": "python-coverage-pytest",
    },
    "libcst": {
        "packages": ("libcst",),
        "default_package": "libcst",
        "config": "libcst",
        "role": "concrete_syntax",
        "verification_id": None,
    },
    "mypy": {
        "packages": ("mypy",),
        "default_package": "mypy",
        "config": "mypy",
        "role": "typecheck",
        "verification_id": "python-mypy",
    },
    "pyright": {
        "packages": ("pyright",),
        "default_package": "pyright",
        "config": "pyright",
        "role": "typecheck",
        "verification_id": "python-pyright",
    },
    "ruff": {
        "packages": ("ruff",),
        "default_package": "ruff",
        "config": "ruff",
        "role": "lint",
        "verification_id": "python-ruff-check",
    },
    "vulture": {
        "packages": ("vulture",),
        "default_package": "vulture",
        "config": "vulture",
        "role": "dead_code",
        "verification_id": "python-vulture",
    },
}
_QUALITY_VERIFICATION_COMMANDS = {
    "python-coverage-pytest": (
        "Run Python coverage with pytest",
        "test",
        ("-m", "coverage", "run", "-m", "pytest", "-q"),
    ),
    "python-mypy": (
        "Run mypy type checking",
        "typecheck",
        ("-m", "mypy", "."),
    ),
    "python-pyright": (
        "Run Pyright type checking",
        "typecheck",
        ("-m", "pyright", "."),
    ),
    "python-ruff-check": (
        "Run Ruff lint checks",
        "lint",
        ("-m", "ruff", "check", "."),
    ),
    "python-vulture": (
        "Run Vulture dead-code analysis",
        "lint",
        ("-m", "vulture", ".", "--min-confidence", "80"),
    ),
}


@dataclass(frozen=True, slots=True)
class QualityToolEvidence:
    id: str
    package: str
    role: str
    source_path: str
    declared_via: str
    confidence: Confidence
    verification_id: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json_value(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class VerificationDiscoveryResult:
    declarations: tuple[VerificationDeclaration, ...]
    quality_tools: tuple[QualityToolEvidence, ...]
    evidence_sources: tuple[str, ...]
    files_considered: int
    files_skipped: int
    diagnostics: tuple[ProjectDiagnostic, ...]
    truncated: bool

    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json_value(getattr(self, field.name)) for field in fields(self)}


class VerificationDiscoveryService:
    def __init__(
        self,
        *,
        authority: ReadAuthority,
        settings: DiscoverSettings,
        max_candidates: int | None = None,
    ) -> None:
        if max_candidates is not None and (
            isinstance(max_candidates, bool)
            or not isinstance(max_candidates, int)
            or max_candidates <= 0
        ):
            raise ValueError("max_candidates must be a positive integer")
        self._authority = authority
        self._settings = settings
        self.max_candidates = min(
            max_candidates or settings.limits.max_evidence,
            settings.limits.max_evidence,
        )

    def discover(
        self,
        project_path: str,
        snapshot: RepositorySnapshot,
    ) -> VerificationDiscoveryResult:
        contents: dict[str, str] = {}
        diagnostics: list[ProjectDiagnostic] = []
        skipped = 0
        for record in snapshot.files:
            if not self._relevant(record.label):
                continue
            try:
                contents[record.label] = self._authority.read_relative_text(
                    project_path,
                    record.label,
                    max_bytes=self._settings.limits.max_file_bytes,
                ).content
            except DiscoverError:
                skipped += 1
                diagnostics.append(
                    ProjectDiagnostic(
                        code="WORKFLOW_SOURCE_SKIPPED",
                        message="One authorized workflow evidence file could not be read.",
                        severity=Severity.WARNING,
                        path=record.label,
                    )
                )

        declarations: dict[str, VerificationDeclaration] = {}
        quality_tools: dict[str, QualityToolEvidence] = {}
        evidence_sources: set[str] = set()
        self._discover_python(
            contents,
            declarations,
            quality_tools,
            evidence_sources,
            diagnostics,
        )
        self._discover_node(contents, declarations, evidence_sources, diagnostics)
        self._discover_powershell(contents, declarations, evidence_sources)
        self._discover_ci(contents, declarations, evidence_sources)

        ordered = sorted(declarations.values(), key=lambda item: item.id)
        truncated = snapshot.truncated or len(ordered) > self.max_candidates
        if len(ordered) > self.max_candidates:
            ordered = ordered[: self.max_candidates]
            diagnostics.append(
                ProjectDiagnostic(
                    code="WORKFLOW_DISCOVERY_LIMIT_REACHED",
                    message="Additional workflow candidates were omitted by the configured limit.",
                    severity=Severity.WARNING,
                )
            )
        if snapshot.truncated:
            diagnostics.append(
                ProjectDiagnostic(
                    code="WORKFLOW_DISCOVERY_FILE_LIMIT_REACHED",
                    message="Workflow evidence may be incomplete because repository scanning was truncated.",
                    severity=Severity.WARNING,
                )
            )
        diagnostics.sort(key=lambda item: (item.code, (item.path or "").casefold()))
        return VerificationDiscoveryResult(
            declarations=tuple(ordered),
            quality_tools=tuple(sorted(quality_tools.values(), key=lambda item: item.id)),
            evidence_sources=tuple(sorted(evidence_sources)),
            files_considered=len(contents),
            files_skipped=skipped,
            diagnostics=tuple(diagnostics),
            truncated=truncated,
        )

    @staticmethod
    def _relevant(label: str) -> bool:
        lowered = label.casefold()
        name = lowered.rsplit("/", 1)[-1]
        return (
            name in {"package.json", "pyproject.toml", "repository.ps1", "uv.lock"}
            or lowered in {"scripts/verify.ps1", "scripts/verify.py"}
            or (
                lowered.startswith("tests/")
                and lowered.endswith(".py")
                and name.startswith("test")
            )
            or (
                lowered.startswith(".github/workflows/")
                and lowered.endswith((".yml", ".yaml"))
            )
        )

    def _discover_python(
        self,
        contents: dict[str, str],
        declarations: dict[str, VerificationDeclaration],
        quality_tools: dict[str, QualityToolEvidence],
        evidence_sources: set[str],
        diagnostics: list[ProjectDiagnostic],
    ) -> None:
        pyproject = contents.get("pyproject.toml")
        if pyproject is not None:
            evidence_sources.add("pyproject")
            try:
                parsed_pyproject = tomllib.loads(pyproject)
            except tomllib.TOMLDecodeError:
                diagnostics.append(
                    ProjectDiagnostic(
                        code="WORKFLOW_PYPROJECT_INVALID",
                        message="pyproject.toml could not be parsed for workflow discovery.",
                        severity=Severity.WARNING,
                        path="pyproject.toml",
                    )
                )
            else:
                for item in _quality_tool_evidence(parsed_pyproject):
                    quality_tools[item.id] = item
                    if item.verification_id is not None:
                        title, category, arguments = _QUALITY_VERIFICATION_COMMANDS[
                            item.verification_id
                        ]
                        self._add(
                            declarations,
                            self._declaration(
                                id=item.verification_id,
                                title=title,
                                category=category,
                                source_path=item.source_path,
                                profile="python",
                                arguments=arguments,
                                provenance=ProvenanceKind.DECLARED,
                                confidence=item.confidence,
                            ),
                        )
                if quality_tools:
                    evidence_sources.add("python_quality_tools")
        if "uv.lock" in contents:
            evidence_sources.add("uv")
            self._add(
                declarations,
                self._declaration(
                    id="python-uv-lock-check",
                    title="Verify Python dependency lock",
                    category="dependency",
                    source_path="uv.lock",
                    profile="uv",
                    arguments=("lock", "--check"),
                    provenance=ProvenanceKind.DECLARED,
                    confidence=Confidence.HIGH,
                ),
            )

        test_files = {
            label: content
            for label, content in contents.items()
            if label.casefold().startswith("tests/")
            and label.casefold().endswith(".py")
            and label.rsplit("/", 1)[-1].casefold().startswith("test")
        }
        if test_files:
            evidence_sources.add("python_tests")
            combined = "\n".join(test_files.values())
            source = sorted(test_files, key=str.casefold)[0]
            if "pytest" in combined or (pyproject is not None and "pytest" in pyproject):
                self._add(
                    declarations,
                    self._declaration(
                        id="python-pytest",
                        title="Run Python pytest suite",
                        category="test",
                        source_path=source,
                        profile="python",
                        arguments=("-m", "pytest", "-q"),
                        provenance=ProvenanceKind.DECLARED,
                        confidence=Confidence.HIGH,
                    ),
                )
            if "unittest" in combined or "unittest.TestCase" in combined:
                self._add(
                    declarations,
                    self._declaration(
                        id="python-unittest-discover",
                        title="Run Python unittest discovery",
                        category="test",
                        source_path=source,
                        profile="python",
                        arguments=("-m", "unittest", "discover", "-s", "tests", "-v"),
                        provenance=ProvenanceKind.DECLARED,
                        confidence=Confidence.HIGH,
                    ),
                )

        if "scripts/verify.py" in contents:
            self._add(
                declarations,
                self._declaration(
                    id="python-module-verify",
                    title="Run Python verification module",
                    category="repository_verification",
                    source_path="scripts/verify.py",
                    profile="python",
                    arguments=("-m", "scripts.verify"),
                    provenance=ProvenanceKind.DECLARED,
                    confidence=Confidence.HIGH,
                ),
            )

    def _discover_node(
        self,
        contents: dict[str, str],
        declarations: dict[str, VerificationDeclaration],
        evidence_sources: set[str],
        diagnostics: list[ProjectDiagnostic],
    ) -> None:
        raw = contents.get("package.json")
        if raw is None:
            return
        evidence_sources.add("package_json")
        try:
            package = json.loads(raw)
        except json.JSONDecodeError:
            diagnostics.append(
                ProjectDiagnostic(
                    code="WORKFLOW_PACKAGE_JSON_INVALID",
                    message="package.json could not be parsed for workflow discovery.",
                    severity=Severity.WARNING,
                    path="package.json",
                )
            )
            return
        scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
        if not isinstance(scripts, dict):
            return
        for name in sorted(scripts, key=str.casefold):
            command = scripts[name]
            if not isinstance(name, str) or not isinstance(command, str) or not command.strip():
                continue
            self._add(
                declarations,
                self._declaration(
                    id=f"node-script-{_slug(name)}",
                    title=f"Run package script {name}",
                    category=_script_category(name),
                    source_path="package.json",
                    profile="npm",
                    arguments=("run", name),
                    provenance=ProvenanceKind.DECLARED,
                    confidence=Confidence.HIGH,
                ),
            )

    def _discover_powershell(
        self,
        contents: dict[str, str],
        declarations: dict[str, VerificationDeclaration],
        evidence_sources: set[str],
    ) -> None:
        if "repository.ps1" in contents:
            evidence_sources.add("powershell")
            self._add(
                declarations,
                self._declaration(
                    id="powershell-repository-check",
                    title="Run repository governance check",
                    category="repository_verification",
                    source_path="repository.ps1",
                    profile="powershell_verify",
                    arguments=("-NoProfile", "-File", ".\\repository.ps1", "check-full"),
                    provenance=ProvenanceKind.DECLARED,
                    confidence=Confidence.HIGH,
                ),
            )
        if "scripts/verify.ps1" in contents:
            evidence_sources.add("powershell")
            self._add(
                declarations,
                self._declaration(
                    id="powershell-verify-script",
                    title="Run repository verification script",
                    category="repository_verification",
                    source_path="scripts/verify.ps1",
                    profile="powershell_verify",
                    arguments=("-NoProfile", "-File", ".\\scripts\\verify.ps1"),
                    provenance=ProvenanceKind.DECLARED,
                    confidence=Confidence.HIGH,
                ),
            )

    def _discover_ci(
        self,
        contents: dict[str, str],
        declarations: dict[str, VerificationDeclaration],
        evidence_sources: set[str],
    ) -> None:
        workflows = {
            label: content
            for label, content in contents.items()
            if label.casefold().startswith(".github/workflows/")
        }
        if not workflows:
            return
        evidence_sources.add("github_actions")
        for label, content in sorted(workflows.items()):
            for command in _github_run_blocks(content):
                lowered = command.casefold()
                if "python -m pytest" in lowered:
                    self._add(
                        declarations,
                        self._declaration(
                            id="python-pytest",
                            title="Run Python pytest suite",
                            category="test",
                            source_path=label,
                            profile="python",
                            arguments=("-m", "pytest", "-q"),
                            provenance=ProvenanceKind.INFERRED,
                            confidence=Confidence.MEDIUM,
                        ),
                    )
                if "python -m unittest" in lowered:
                    self._add(
                        declarations,
                        self._declaration(
                            id="python-unittest-discover",
                            title="Run Python unittest discovery",
                            category="test",
                            source_path=label,
                            profile="python",
                            arguments=("-m", "unittest", "discover", "-s", "tests", "-v"),
                            provenance=ProvenanceKind.INFERRED,
                            confidence=Confidence.MEDIUM,
                        ),
                    )

    @staticmethod
    def _declaration(
        *,
        id: str,
        title: str,
        category: str,
        source_path: str,
        profile: str,
        arguments: tuple[str, ...],
        provenance: ProvenanceKind,
        confidence: Confidence,
    ) -> VerificationDeclaration:
        return VerificationDeclaration(
            id=id,
            category=category,
            title=title,
            authority="discovered_only",
            execution_available=False,
            source_path=source_path,
            profile=profile,
            arguments=arguments,
            provenance=provenance,
            confidence=confidence,
            evidence_ids=(),
        )

    @staticmethod
    def _add(
        declarations: dict[str, VerificationDeclaration],
        declaration: VerificationDeclaration,
    ) -> None:
        declarations.setdefault(declaration.id, declaration)


def _normalize_requirement_name(requirement: str) -> str | None:
    match = _REQUIREMENT_NAME.match(requirement)
    if match is None:
        return None
    return re.sub(r"[-_.]+", "-", match.group(1)).casefold()


def _dependency_sources(pyproject: dict[str, Any]) -> dict[str, str]:
    sources: dict[str, str] = {}

    def add(requirements: Any, source: str) -> None:
        if not isinstance(requirements, list):
            return
        for requirement in requirements:
            if not isinstance(requirement, str):
                continue
            name = _normalize_requirement_name(requirement)
            if name:
                sources.setdefault(name, source)

    project = pyproject.get("project")
    if isinstance(project, dict):
        add(project.get("dependencies"), "project_dependency")
        optional = project.get("optional-dependencies")
        if isinstance(optional, dict):
            for group in sorted(optional, key=str.casefold):
                add(optional[group], f"optional_dependency:{group}")

    groups = pyproject.get("dependency-groups")
    if isinstance(groups, dict):
        for group in sorted(groups, key=str.casefold):
            add(groups[group], f"dependency_group:{group}")
    return sources


def _quality_tool_evidence(pyproject: dict[str, Any]) -> tuple[QualityToolEvidence, ...]:
    dependencies = _dependency_sources(pyproject)
    tool_section = pyproject.get("tool")
    configured = tool_section if isinstance(tool_section, dict) else {}
    records: list[QualityToolEvidence] = []
    for tool_id in sorted(_QUALITY_TOOL_SPECS):
        spec = _QUALITY_TOOL_SPECS[tool_id]
        package = next(
            (candidate for candidate in spec["packages"] if candidate in dependencies),
            None,
        )
        if package is not None:
            declared_via = dependencies[package]
            confidence = Confidence.HIGH
        elif spec["config"] in configured:
            package = str(spec["default_package"])
            declared_via = f"tool_config:{spec['config']}"
            confidence = Confidence.MEDIUM
        else:
            continue
        records.append(
            QualityToolEvidence(
                id=tool_id,
                package=package,
                role=str(spec["role"]),
                source_path="pyproject.toml",
                declared_via=declared_via,
                confidence=confidence,
                verification_id=spec["verification_id"],
            )
        )
    return tuple(records)


def _github_run_blocks(content: str) -> tuple[str, ...]:
    lines = content.splitlines()
    results: list[str] = []
    block_markers = {"|", ">", "|-", ">-", "|+", ">+"}
    index = 0
    while index < len(lines):
        raw = lines[index]
        stripped = raw.lstrip()
        indent = len(raw) - len(stripped)
        marker = stripped[2:].lstrip() if stripped.startswith("- ") else stripped
        if not marker.startswith("run:"):
            index += 1
            continue
        remainder = marker[4:].strip()
        if remainder not in block_markers:
            if remainder:
                results.append(remainder)
            index += 1
            continue
        block: list[str] = []
        index += 1
        while index < len(lines):
            current = lines[index]
            if not current.strip():
                index += 1
                continue
            current_indent = len(current) - len(current.lstrip())
            if current_indent <= indent:
                break
            block.append(current.strip())
            index += 1
        if block:
            results.append(" ".join(block))
    return tuple(results)


def _script_category(name: str) -> str:
    if name in _SCRIPT_CATEGORY:
        return _SCRIPT_CATEGORY[name]
    return _SCRIPT_CATEGORY.get(name.split(":", 1)[0], "project_command")


def _slug(value: str) -> str:
    return _SAFE_ID.sub("-", value.casefold()).strip("-") or "workflow"


def _json_value(value: Any) -> Any:
    if hasattr(value, "to_json_dict"):
        return value.to_json_dict()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"value is not JSON-compatible: {type(value).__name__}")


__all__ = [
    "QualityToolEvidence",
    "VerificationDiscoveryResult",
    "VerificationDiscoveryService",
]
