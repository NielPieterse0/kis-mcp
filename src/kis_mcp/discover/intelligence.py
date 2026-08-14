from __future__ import annotations

import hashlib
import json
import ntpath
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..evidence import EvidenceCorruptionError, EvidenceStore
from ..projects import (
    ProjectDefinition,
    ProjectRecoveryCapsule,
    ProjectRegistry,
    RecoveryIdentity,
)
from .analyzers.contracts import AnalysisContext, AnalyzerOutput
from .analyzers.dependencies import DependencyImportsAnalyzer
from .contracts import GitSummary, ProjectDiagnostic, ProjectIdentity, Severity
from .errors import DiscoverError
from .git_reader import GitReader
from .intelligence_contracts import ProjectIntelligenceRuntime
from .python_index import (
    PythonCallEdge,
    PythonImportRecord,
    PythonInheritanceEdge,
    PythonModuleRecord,
    PythonProjectIndexResult,
    PythonProjectIndexer,
    PythonSymbolRecord,
)
from .read_authority import ReadAuthority
from .scanner import RepositoryScanner, RepositorySnapshot
from .semantic import NullSemanticProvider, SemanticEvidence, SemanticEvidenceProvider
from .settings import DiscoverSettings

_INDEX_VERSION = "discover-project-intelligence-v1"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _normalized_path(value: str) -> str:
    return ntpath.normcase(ntpath.normpath(value))


def _registered_project(
    projects: ProjectRegistry | None,
    canonical_path: str,
) -> ProjectDefinition | None:
    if projects is None:
        return None
    target = _normalized_path(canonical_path)
    for project in projects.projects:
        root = _normalized_path(project.local_root)
        if target == root:
            return project
        try:
            relative = ntpath.relpath(target, root)
        except ValueError:
            continue
        parts = tuple(part.casefold() for part in relative.split("\\") if part)
        if len(parts) == 3 and parts[:2] == (".work", "worktrees"):
            return project
    return None


def _project_identity(
    snapshot: RepositorySnapshot,
    git: GitSummary,
    definition: ProjectDefinition | None,
) -> ProjectIdentity:
    if definition is None:
        return replace(
            snapshot.project,
            git_root=snapshot.project.canonical_path if git.repository else None,
            remote_identity=git.remote,
        )
    return ProjectIdentity(
        project_id=definition.project_id,
        canonical_path=snapshot.project.canonical_path,
        repository_root=definition.local_root,
        git_root=snapshot.project.canonical_path if git.repository else None,
        remote_identity=(
            definition.github.repository
            if definition.github is not None
            else git.remote
        ),
    )


def _provider_fingerprint(provider: SemanticEvidenceProvider) -> str:
    return _fingerprint(
        {
            "provider_id": provider.provider_id,
            "provider_version": provider.provider_version,
            "state": str(getattr(provider, "state_fingerprint", "unknown")),
        }
    )


def _settings_fingerprint(settings: DiscoverSettings) -> str:
    return _fingerprint(
        {
            "index_version": _INDEX_VERSION,
            "discover": asdict(settings),
        }
    )


def _source_fingerprint(
    *,
    authority: ReadAuthority,
    project_path: str,
    snapshot: RepositorySnapshot,
    git_reader: GitReader,
    git: GitSummary,
    settings: DiscoverSettings,
) -> str:
    topology = [(item.label, item.size) for item in snapshot.files]
    payload: dict[str, Any] = {
        "head": git.head,
        "status": git.status,
        "topology": topology,
        "truncation": list(snapshot.truncation_reasons),
    }
    labels = {item.label for item in snapshot.files}
    paths_to_hash: set[str] = set()
    if git.repository and git.available and git.status == "dirty":
        changes = git_reader.inspect_local_changes(project_path)
        payload["changes"] = changes.to_json_dict()
        for item in changes.changes:
            if item.path in labels:
                paths_to_hash.add(item.path)
            if item.previous_path in labels:
                paths_to_hash.add(item.previous_path)
    elif not git.repository or not git.available:
        paths_to_hash.update(labels)
    digests: dict[str, str] = {}
    for label in sorted(paths_to_hash, key=str.casefold):
        try:
            content = authority.read_relative_text(
                project_path,
                label,
                max_bytes=settings.limits.max_file_bytes,
            ).content.encode("utf-8")
        except DiscoverError:
            digests[label] = "unreadable"
            continue
        digests[label] = hashlib.sha256(content).hexdigest()
    payload["content_sha256"] = digests
    return _fingerprint(payload)


def _javascript_dependencies(
    *,
    authority: ReadAuthority,
    settings: DiscoverSettings,
    project_path: str,
    snapshot: RepositorySnapshot,
    index: PythonProjectIndexResult,
) -> tuple[dict[str, Any], ...]:
    output = DependencyImportsAnalyzer().analyze(
        AnalysisContext(
            snapshot=snapshot,
            authority=authority,
            project_path=project_path,
            python_index=index,
            verification=(),
            changed_paths=(),
            analyzer_options={
                "dependencies.imports": {
                    "max_edges": settings.memory.max_relationships,
                }
            },
        ),
        {"architecture.components": AnalyzerOutput("architecture.components")},
    )
    return tuple(
        dict(item)
        for item in output.facts.get("dependencies", ())
        if item.get("kind") == "javascript_import"
    )


def _relationship(
    *,
    kind: str,
    source: str,
    target: str,
    path: str,
    line: int,
    provider: str,
    provenance: str,
    confidence: str,
    classification: str,
) -> dict[str, Any]:
    identity = f"{kind}:{source}:{target}:{path}:{line}:{provider}"
    return {
        "relationship_id": _fingerprint(identity)[:24],
        "type": kind,
        "source": source,
        "target": target,
        "source_evidence": {"path": path, "line": line},
        "provider": provider,
        "provenance": provenance,
        "confidence": confidence,
        "freshness": "current",
        "classification": classification,
    }


def _build_atlases(
    *,
    authority: ReadAuthority,
    settings: DiscoverSettings,
    project_path: str,
    snapshot: RepositorySnapshot,
    index: PythonProjectIndexResult,
    semantic: SemanticEvidence,
) -> tuple[
    dict[str, Any],
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
    tuple[str, ...],
]:
    file_records = [
        {
            "path": item.label,
            "size": item.size,
            "suffix": item.suffix,
            "category": item.category,
            "freshness": "current",
            "provider": "local_filesystem",
        }
        for item in snapshot.files[: settings.memory.max_files]
    ]
    module_records = [
        {
            **item.to_json_dict(),
            "language": "python",
            "provider": "python_ast",
            "provenance": "deterministic",
            "freshness": "current",
        }
        for item in index.modules[: settings.memory.max_modules]
    ]
    known_module_paths = {str(item["path"]) for item in module_records}
    for item in snapshot.files:
        if len(module_records) >= settings.memory.max_modules:
            break
        if item.suffix.casefold() not in {
            ".js",
            ".jsx",
            ".mjs",
            ".cjs",
            ".ts",
            ".tsx",
            ".mts",
            ".cts",
        }:
            continue
        if item.label in known_module_paths:
            continue
        module_records.append(
            {
                "name": item.label,
                "path": item.label,
                "package": False,
                "language": "typescript"
                if "t" in item.suffix.casefold()
                else "javascript",
                "provider": "static_javascript",
                "provenance": "deterministic",
                "freshness": "current",
            }
        )

    symbols: list[dict[str, Any]] = [
        {
            "symbol_id": _fingerprint(item.qualified_name)[:24],
            **item.to_json_dict(),
            "language": "python",
            "provider": "python_ast",
            "provenance": "deterministic",
            "classification": "deterministic",
            "confidence": "high",
            "freshness": "current",
        }
        for item in index.symbols[: settings.memory.max_symbols]
    ]
    semantic_names = {str(item["qualified_name"]) for item in symbols}
    for item in semantic.symbols:
        if len(symbols) >= settings.memory.max_symbols:
            break
        if item.qualified_name in semantic_names:
            continue
        symbols.append(
            {
                "symbol_id": _fingerprint(
                    f"{semantic.provider_id}:{item.qualified_name}"
                )[:24],
                "qualified_name": item.qualified_name,
                "module": item.path,
                "name": item.name,
                "kind": item.kind,
                "path": item.path,
                "line": item.line,
                "end_line": item.end_line,
                "language": item.language,
                "provider": semantic.provider_id,
                "provenance": "semantic_provider",
                "classification": "semantic",
                "confidence": "medium",
                "freshness": "current",
            }
        )
        semantic_names.add(item.qualified_name)

    relationships: list[dict[str, Any]] = []
    for module in index.modules:
        relationships.append(
            _relationship(
                kind="file_module",
                source=module.path,
                target=module.name,
                path=module.path,
                line=1,
                provider="python_ast",
                provenance="python_ast",
                confidence="high",
                classification="deterministic",
            )
        )
    for item in index.symbols:
        relationships.append(
            _relationship(
                kind="module_symbol",
                source=item.module,
                target=item.qualified_name,
                path=item.path,
                line=item.line,
                provider="python_ast",
                provenance="python_ast",
                confidence="high",
                classification="deterministic",
            )
        )
    for item in index.imports:
        relationships.append(
            _relationship(
                kind="import",
                source=item.source_module,
                target=item.target_module or item.imported_name or "unknown",
                path=item.path,
                line=item.line,
                provider="python_ast",
                provenance="python_ast",
                confidence="high" if item.internal else "medium",
                classification="deterministic",
            )
        )
    for item in index.inheritance:
        relationships.append(
            _relationship(
                kind="inheritance",
                source=item.symbol,
                target=item.base,
                path=item.path,
                line=item.line,
                provider="python_ast",
                provenance="python_ast",
                confidence="high",
                classification="deterministic",
            )
        )
    for item in index.calls:
        relationships.append(
            _relationship(
                kind="call",
                source=item.caller,
                target=item.callee,
                path=item.path,
                line=item.line,
                provider="python_ast",
                provenance="python_ast",
                confidence="high",
                classification="deterministic",
            )
        )
    for item in _javascript_dependencies(
        authority=authority,
        settings=settings,
        project_path=project_path,
        snapshot=snapshot,
        index=index,
    ):
        relationships.append(
            _relationship(
                kind="import",
                source=str(item["source"]),
                target=str(item["target"]),
                path=str(item["source"]),
                line=int(item.get("line", 1)),
                provider="static_javascript",
                provenance="static_javascript_import",
                confidence="high",
                classification="deterministic",
            )
        )
    for item in semantic.relationships:
        relationships.append(
            _relationship(
                kind=item.kind,
                source=item.source,
                target=item.target,
                path=item.path,
                line=item.line,
                provider=semantic.provider_id,
                provenance="semantic_provider",
                confidence="medium",
                classification="semantic",
            )
        )

    source_files = tuple(item for item in snapshot.files if item.category == "source")
    tests = tuple(item for item in snapshot.files if item.category == "test")
    for test in tests:
        test_stem = (
            Path(test.label).stem.casefold().removeprefix("test_").removesuffix("_test")
        )
        for source in source_files:
            if not test_stem or test_stem != Path(source.label).stem.casefold():
                continue
            relationships.append(
                _relationship(
                    kind="test_targets",
                    source=test.label,
                    target=source.label,
                    path=test.label,
                    line=1,
                    provider="repository_convention",
                    provenance="test_filename_convention",
                    confidence="medium",
                    classification="heuristic",
                )
            )

    relationships.sort(
        key=lambda item: (
            str(item["type"]),
            str(item["source"]).casefold(),
            str(item["target"]).casefold(),
            str(item["source_evidence"]["path"]).casefold(),
            int(item["source_evidence"]["line"]),
        )
    )
    reasons = set(snapshot.truncation_reasons)
    reasons.update(index.truncation_reasons)
    if len(snapshot.files) > len(file_records):
        reasons.add("memory_max_files")
    if len(index.modules) > settings.memory.max_modules:
        reasons.add("memory_max_modules")
    if len(index.symbols) + len(semantic.symbols) > len(symbols):
        reasons.add("memory_max_symbols")
    if len(relationships) > settings.memory.max_relationships:
        reasons.add("memory_max_relationships")
    relationships = relationships[: settings.memory.max_relationships]

    python_payload = index.to_json_dict()
    code_atlas = {
        **python_payload,
        "schema_version": 1,
        "files": file_records,
        "directories": list(snapshot.directories),
        "persistent_modules": module_records,
        "python_index": python_payload,
        "truncated": bool(reasons),
        "truncation_reasons": sorted(reasons),
    }
    return code_atlas, tuple(symbols), tuple(relationships), tuple(sorted(reasons))


def _python_index_from_json(value: Any) -> PythonProjectIndexResult:
    if not isinstance(value, dict):
        raise EvidenceCorruptionError("persisted Python index is not an object")
    try:
        return PythonProjectIndexResult(
            status=str(value["status"]),
            language=str(value["language"]),
            modules=tuple(PythonModuleRecord(**item) for item in value["modules"]),
            symbols=tuple(PythonSymbolRecord(**item) for item in value["symbols"]),
            imports=tuple(PythonImportRecord(**item) for item in value["imports"]),
            inheritance=tuple(
                PythonInheritanceEdge(**item) for item in value["inheritance"]
            ),
            calls=tuple(PythonCallEdge(**item) for item in value["calls"]),
            diagnostics=tuple(
                ProjectDiagnostic(
                    code=str(item["code"]),
                    message=str(item["message"]),
                    severity=Severity(str(item["severity"])),
                    path=item.get("path"),
                )
                for item in value["diagnostics"]
            ),
            summary={str(key): int(item) for key, item in value["summary"].items()},
            truncated=bool(value["truncated"]),
            truncation_reasons=tuple(str(item) for item in value["truncation_reasons"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise EvidenceCorruptionError(
            "persisted Python index contract is corrupt"
        ) from exc


def _semantic_from_payload(value: Any) -> SemanticEvidence:
    if not isinstance(value, dict):
        raise EvidenceCorruptionError("persisted semantic metadata is corrupt")
    return SemanticEvidence(
        provider_id=str(value.get("provider_id", "none")),
        provider_version=str(value.get("provider_version", "0")),
        status=str(value.get("status", "unavailable")),
        unknowns=tuple(str(item) for item in value.get("unknowns", ())),
    )


def _publish_recovery_hint(
    *,
    definition: ProjectDefinition | None,
    project: ProjectIdentity,
    git: GitSummary,
    source_fingerprint: str,
    settings_fingerprint: str,
    provider_fingerprint: str,
    central_generation_id: str | None,
) -> dict[str, Any]:
    if definition is None or central_generation_id is None:
        return {"status": "unavailable", "available": False}
    capsule_root = Path(definition.local_root) / ".temp" / "kis"
    try:
        capsule = ProjectRecoveryCapsule(definition)
        identity = RecoveryIdentity.for_project(
            definition,
            worktree_root=project.canonical_path,
            git_revision=git.head or "unavailable",
            git_status=git.status,
            source_fingerprint=source_fingerprint,
            settings_fingerprint=settings_fingerprint,
            provider_fingerprint=provider_fingerprint,
        )
        snapshot = capsule.publish_discover_hint(
            identity,
            central_generation_id=central_generation_id,
        )
    except Exception as exc:
        return {
            "status": "degraded",
            "available": True,
            "root": str(capsule_root),
            "error": type(exc).__name__,
        }
    return {
        **snapshot.to_json_dict(),
        "available": True,
        "root": str(capsule.root),
    }


class ProjectIntelligenceService:
    def __init__(
        self,
        *,
        boundary: Path,
        settings: DiscoverSettings,
        projects: ProjectRegistry | None = None,
        semantic_provider: SemanticEvidenceProvider | None = None,
    ) -> None:
        self._boundary = boundary
        self._settings = settings
        self._projects = projects
        self._semantic_provider = semantic_provider or NullSemanticProvider()

    def get(self, project_path: str) -> ProjectIntelligenceRuntime:
        authority = ReadAuthority(self._boundary, self._settings)
        snapshot = RepositoryScanner(authority, self._settings).snapshot(project_path)
        git_reader = GitReader(authority=authority, settings=self._settings)
        git = git_reader.inspect(project_path)
        definition = _registered_project(
            self._projects, snapshot.project.canonical_path
        )
        project = _project_identity(snapshot, git, definition)
        source_fingerprint = _source_fingerprint(
            authority=authority,
            project_path=project_path,
            snapshot=snapshot,
            git_reader=git_reader,
            git=git,
            settings=self._settings,
        )
        settings_fingerprint = _settings_fingerprint(self._settings)
        provider_fingerprint = _provider_fingerprint(self._semantic_provider)
        worktree_fingerprint = _fingerprint(project.canonical_path.casefold())
        applicability = {
            "schema_version": self._settings.memory.schema_version,
            "project_id": project.project_id,
            "canonical_repository_root": project.repository_root,
            "canonical_project_root": project.canonical_path,
            "worktree_fingerprint": worktree_fingerprint,
            "git_revision": git.head,
            "git_status": git.status,
            "source_fingerprint": source_fingerprint,
            "discover_settings_fingerprint": settings_fingerprint,
            "parser_index_version": _INDEX_VERSION,
            "semantic_provider_fingerprint": provider_fingerprint,
        }
        applicability_fingerprint = _fingerprint(applicability)
        persistence_enabled = self._settings.memory.enabled and definition is not None
        namespace = (
            f"projects/{project.project_id}/{worktree_fingerprint[:24]}"
            if persistence_enabled
            else None
        )
        current_generation = None
        recovered_pointer = None
        store = None
        if namespace is not None:
            store = EvidenceStore(
                Path(self._settings.memory.state_root),
                max_file_bytes=self._settings.memory.max_stored_bytes,
                max_total_bytes=self._settings.memory.max_stored_bytes,
            )
            try:
                current_generation = store.read_current_generation(namespace)
            except FileNotFoundError:
                current_generation = None
            except EvidenceCorruptionError:
                if self._settings.memory.corruption_handling == "fail_closed":
                    raise
                recovered_pointer = store.retain_corrupt_current_pointer(namespace)
                current_generation = None

        if (
            current_generation is not None
            and current_generation.metadata.get("applicability_fingerprint")
            == applicability_fingerprint
        ):
            try:
                code_atlas = json.loads(current_generation.artifacts["code-atlas.json"])
                symbol_payload = json.loads(
                    current_generation.artifacts["symbol-atlas.json"]
                )
                relationship_payload = json.loads(
                    current_generation.artifacts["relationship-graph.json"]
                )
                index = _python_index_from_json(code_atlas["python_index"])
                semantic = _semantic_from_payload(symbol_payload["semantic"])
                symbols = tuple(dict(item) for item in symbol_payload["symbols"])
                relationships = tuple(
                    dict(item) for item in relationship_payload["relationships"]
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                if self._settings.memory.corruption_handling == "fail_closed":
                    raise EvidenceCorruptionError(
                        "persisted Discover generation is corrupt"
                    ) from exc
                recovered_pointer = (
                    store.retain_corrupt_current_pointer(namespace) if store else None
                )
                current_generation = None
            else:
                reusable_semantic = not (
                    semantic.status == "degraded"
                    and self._semantic_provider.provider_id != "none"
                )
                if reusable_semantic:
                    return ProjectIntelligenceRuntime(
                        project=project,
                        snapshot=replace(snapshot, project=project),
                        python_index=index,
                        git=git,
                        code_atlas=code_atlas,
                        symbol_atlas=symbols,
                        relationship_graph=relationships,
                        semantic=semantic,
                        persistence={
                            "status": "reused",
                            "available": True,
                            "current": True,
                            "namespace": namespace,
                            "generation_id": current_generation.generation_id,
                            "applicability_fingerprint": applicability_fingerprint,
                            "recovery_capsule": _publish_recovery_hint(
                                definition=definition,
                                project=project,
                                git=git,
                                source_fingerprint=source_fingerprint,
                                settings_fingerprint=settings_fingerprint,
                                provider_fingerprint=provider_fingerprint,
                                central_generation_id=current_generation.generation_id,
                            ),
                        },
                        source_fingerprint=source_fingerprint,
                        settings_fingerprint=settings_fingerprint,
                        provider_fingerprint=provider_fingerprint,
                        truncated=bool(code_atlas.get("truncated", False)),
                        truncation_reasons=tuple(
                            code_atlas.get("truncation_reasons", ())
                        ),
                    )

        try:
            semantic = self._semantic_provider.read(
                project_path,
                tuple(
                    item.label for item in snapshot.files if item.category == "source"
                )[: self._settings.memory.max_files],
            )
        except Exception as exc:
            semantic = SemanticEvidence(
                provider_id=self._semantic_provider.provider_id,
                provider_version=self._semantic_provider.provider_version,
                status="degraded",
                unknowns=(
                    f"Optional semantic provider failed independently: {type(exc).__name__}.",
                ),
            )
        index = PythonProjectIndexer(
            authority=authority,
            settings=self._settings,
        ).index(project_path, snapshot)
        code_atlas, symbols, relationships, reasons = _build_atlases(
            authority=authority,
            settings=self._settings,
            project_path=project_path,
            snapshot=snapshot,
            index=index,
            semantic=semantic,
        )
        semantic_payload = {
            "provider_id": semantic.provider_id,
            "provider_version": semantic.provider_version,
            "status": semantic.status,
            "unknowns": list(semantic.unknowns),
        }
        status = "unregistered" if definition is None else "disabled"
        generation_id = None
        if namespace is not None and store is not None:
            metadata = {
                **applicability,
                "applicability_fingerprint": applicability_fingerprint,
                "generation_timestamp": datetime.now(UTC).isoformat(),
                "freshness_status": "current",
                "truncation_state": {
                    "truncated": bool(reasons),
                    "reasons": list(reasons),
                },
                "provenance": {
                    "filesystem": "bounded_local_filesystem",
                    "git": "local_git",
                    "deterministic_parser": "python_ast_and_static_javascript",
                    "semantic_provider": semantic.provider_id,
                },
                "semantic_provider_identity": semantic.provider_id,
                "semantic_provider_version": semantic.provider_version,
                "semantic_provider_status": semantic.status,
            }
            written = store.write_generation(
                namespace,
                metadata=metadata,
                artifacts={
                    "code-atlas.json": _canonical_json(code_atlas),
                    "symbol-atlas.json": _canonical_json(
                        {"symbols": list(symbols), "semantic": semantic_payload}
                    ),
                    "relationship-graph.json": _canonical_json(
                        {"relationships": list(relationships)}
                    ),
                },
                expected_current_generation=(
                    current_generation.generation_id
                    if current_generation is not None
                    else None
                ),
            )
            generation_id = written.generation_id
            status = (
                "created" if written.previous_generation_id is None else "refreshed"
            )

        persistence = {
            "status": status,
            "available": namespace is not None,
            "current": True,
            "namespace": namespace,
            "generation_id": generation_id,
            "applicability_fingerprint": applicability_fingerprint,
            "recovery_capsule": _publish_recovery_hint(
                definition=definition,
                project=project,
                git=git,
                source_fingerprint=source_fingerprint,
                settings_fingerprint=settings_fingerprint,
                provider_fingerprint=provider_fingerprint,
                central_generation_id=generation_id,
            ),
        }
        if recovered_pointer is not None:
            persistence["recovered_pointer"] = recovered_pointer
        return ProjectIntelligenceRuntime(
            project=project,
            snapshot=replace(snapshot, project=project),
            python_index=index,
            git=git,
            code_atlas=code_atlas,
            symbol_atlas=symbols,
            relationship_graph=relationships,
            semantic=semantic,
            persistence=persistence,
            source_fingerprint=source_fingerprint,
            settings_fingerprint=settings_fingerprint,
            provider_fingerprint=provider_fingerprint,
            truncated=bool(reasons),
            truncation_reasons=reasons,
        )


__all__ = ["ProjectIntelligenceService"]
