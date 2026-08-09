from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

from .context_contracts import (
    CodeContextBudget,
    ContextFile,
    ContextModule,
    ContextOmissions,
    ContextProvenance,
    ContextRelationship,
    ContextSymbol,
    ContextUnknown,
    GetCodeContextRequest,
    GetCodeContextResponse,
)
from .context_ranking import (
    relevance_sort_key,
    score_named_candidate,
    score_path_candidate,
    score_relationship_candidate,
    stable_fingerprint,
    task_terms,
)
from .contracts import Confidence, GitSummary, ProjectIdentity
from .errors import DiscoverError
from .git_reader import GitReader
from .intelligence import ProjectIntelligenceService
from .python_index import (
    PythonModuleRecord,
    PythonProjectIndexResult,
    PythonProjectIndexer,
    PythonSymbolRecord,
)
from .read_authority import ReadAuthority
from .scanner import RepositoryScanner, RepositorySnapshot, ScannedFile
from .settings import DiscoverSettings


_MIN_EXCERPT_CHARS = 120
_MAX_INITIAL_EXCERPT_CHARS = 1_200


@dataclass(frozen=True, slots=True)
class _FileCandidate:
    record: ScannedFile
    category: str
    score: int
    matched_terms: tuple[str, ...]
    git_changed: bool


@dataclass(frozen=True, slots=True)
class _ModuleCandidate:
    record: PythonModuleRecord
    score: int
    matched_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _SymbolCandidate:
    record: PythonSymbolRecord
    score: int
    matched_terms: tuple[str, ...]
    provider: str = "python_ast"
    provenance: str = "parser_confirmed"


@dataclass(frozen=True, slots=True)
class _RelationshipCandidate:
    kind: str
    source: str
    target: str
    path: str
    line: int
    score: int
    confidence: str
    provider: str = "python_ast"
    provenance: str = "parser_confirmed"


class ContextBrokerService:
    """Assemble the smallest sufficient local evidence bundle for one task."""

    def __init__(
        self,
        *,
        boundary: Path,
        settings: DiscoverSettings,
        intelligence_service: ProjectIntelligenceService | None = None,
    ) -> None:
        self._boundary = boundary
        self._settings = settings
        self._intelligence = intelligence_service or ProjectIntelligenceService(
            boundary=boundary,
            settings=settings,
        )

    def use_intelligence_service(
        self,
        intelligence_service: ProjectIntelligenceService,
    ) -> None:
        self._intelligence = intelligence_service

    def get(self, request: GetCodeContextRequest) -> GetCodeContextResponse:
        if not self._settings.enabled:
            raise DiscoverError(
                code="DISCOVER_DISABLED",
                message="Discover is disabled by runtime settings.",
                reason="settings.discover.enabled is false.",
                field="settings.discover.enabled",
            )
        self._validate_budget(request.budget)

        intelligence = self._intelligence.get(request.project)
        authority = ReadAuthority(self._boundary, self._settings)
        snapshot = intelligence.snapshot
        python_index = intelligence.python_index
        git_reader = GitReader(authority=authority, settings=self._settings)
        git = intelligence.git
        local_changes = git_reader.inspect_local_changes(request.project)
        changed_paths = {
            path
            for item in local_changes.changes
            for path in (item.path, item.previous_path)
            if path is not None
        }
        project = intelligence.project
        terms = task_terms(request.task)

        module_candidates = self._module_candidates(python_index, terms)
        symbol_candidates = self._symbol_candidates(
            python_index,
            terms,
            intelligence.symbol_atlas,
        )
        files = self._file_candidates(
            snapshot,
            terms,
            changed_paths,
            module_candidates,
            symbol_candidates,
        )
        relevant_files = tuple(item for item in files if item.score >= 10)
        if not relevant_files and files:
            relevant_files = files[:1]
        selected_file_candidates = list(relevant_files[: request.budget.max_files])
        selected_paths = {item.record.label for item in selected_file_candidates}

        selected_modules = [
            item for item in module_candidates if item.record.path in selected_paths
        ]
        selected_symbols = [
            item for item in symbol_candidates if item.record.path in selected_paths
        ][: request.budget.max_symbols]
        relevant_symbols = tuple(
            item
            for item in symbol_candidates
            if item.record.path in {candidate.record.label for candidate in relevant_files}
            and item.score >= 10
        )
        if not relevant_symbols:
            relevant_symbols = tuple(
                item for item in symbol_candidates if item.record.path in selected_paths
            )

        selected_identifiers = {
            *(item.record.name for item in selected_modules),
            *(item.record.qualified_name for item in selected_symbols),
            *(item.record.name for item in selected_symbols),
        }
        relationship_candidates = self._relationship_candidates(
            python_index,
            terms,
            selected_identifiers,
            selected_paths,
            intelligence.relationship_graph,
        )
        relevant_relationships = tuple(
            item
            for item in relationship_candidates
            if item.score > 0 and (
                item.path in {candidate.record.label for candidate in relevant_files}
                or item.source in selected_identifiers
                or item.target in selected_identifiers
            )
        )
        selected_relationships = list(
            relevant_relationships[: request.budget.max_relationships]
        )

        reasons = set(snapshot.truncation_reasons)
        reasons.update(python_index.truncation_reasons)
        if git.truncated or local_changes.truncated:
            reasons.add("git_output")
        if len(relevant_files) > request.budget.max_files:
            reasons.add("max_files")
        if len(relevant_symbols) > request.budget.max_symbols:
            reasons.add("max_symbols")
        if len(relevant_relationships) > request.budget.max_relationships:
            reasons.add("max_relationships")

        excerpt_limit = self._initial_excerpt_limit(
            request.budget,
            len(selected_file_candidates),
        )
        selected_files: list[ContextFile] = []
        unreadable_files = 0
        symbol_focus = self._symbol_focus(selected_symbols)
        for candidate in selected_file_candidates:
            try:
                text = authority.read_relative_text(
                    request.project,
                    candidate.record.label,
                    max_bytes=self._settings.limits.max_file_bytes,
                ).content
            except DiscoverError:
                unreadable_files += 1
                reasons.add("unreadable_files")
                continue
            excerpt, start_line, end_line, truncated = _extract_excerpt(
                text,
                terms=terms,
                focus_lines=symbol_focus.get(candidate.record.label, ()),
                max_chars=excerpt_limit,
            )
            selected_files.append(
                ContextFile(
                    path=candidate.record.label,
                    category=candidate.category,
                    relevance_score=candidate.score,
                    matched_terms=candidate.matched_terms,
                    excerpt=excerpt,
                    start_line=start_line,
                    end_line=end_line,
                    truncated=truncated,
                    provenance=ContextProvenance(
                        kind="observed",
                        provider="local_filesystem",
                        identifier=candidate.record.label,
                    ),
                )
            )

        readable_paths = {item.path for item in selected_files}
        modules = [
            _context_module(item)
            for item in selected_modules
            if item.record.path in readable_paths
        ]
        symbols = [
            _context_symbol(item)
            for item in selected_symbols
            if item.record.path in readable_paths
        ]
        relationships = [
            _context_relationship(item)
            for item in selected_relationships
            if item.path in readable_paths
        ]

        unknowns = self._unknowns(
            snapshot=snapshot,
            python_index=python_index,
            git=git,
            selected_files=selected_files,
            unreadable_files=unreadable_files,
        )
        providers = {
            "filesystem": {
                "available": True,
                "provider": "local_filesystem",
                "authority": "bounded_read",
            },
            "semantic": {
                "available": bool(python_index.modules) or intelligence.semantic.status == "ready",
                "provider": (
                    intelligence.semantic.provider_id
                    if intelligence.semantic.status == "ready"
                    else "python_ast" if python_index.modules else None
                ),
                "fallback": (
                    "python_ast"
                    if intelligence.semantic.status != "ready" and python_index.modules
                    else None
                ),
                "semantic_status": intelligence.semantic.status,
            },
            "project_intelligence": {
                **dict(intelligence.persistence),
                "freshness": "current",
            },
            "git": {
                "available": git.available,
                "provider": "local_git",
            },
            "remote": {
                "available": False,
                "reason": "not_configured",
            },
        }
        git_payload = _compact_git(
            git,
            local_changes.to_json_dict(),
            max_paths=request.budget.max_files,
        )

        return self._compact_response(
            project=project,
            request=request,
            terms=terms,
            files=selected_files,
            modules=modules,
            symbols=symbols,
            relationships=relationships,
            git=git_payload,
            providers=providers,
            unknowns=unknowns,
            reasons=reasons,
            total_files=len(relevant_files),
            total_symbols=len(relevant_symbols),
            total_relationships=len(relevant_relationships),
            unreadable_files=unreadable_files,
            diagnostic_degradation=bool(
                snapshot.truncated
                or python_index.diagnostics
                or git.diagnostics
                or local_changes.diagnostics
            ),
        )

    def _validate_budget(self, budget: CodeContextBudget) -> None:
        maxima = {
            "max_chars": self._settings.limits.max_output_chars,
            "max_files": self._settings.limits.max_files,
            "max_symbols": self._settings.limits.python_max_records,
            "max_relationships": self._settings.limits.python_max_records,
        }
        for field, maximum in maxima.items():
            requested = getattr(budget, field)
            if requested > maximum:
                raise DiscoverError(
                    code="DISCOVER_CONTEXT_BUDGET_INVALID",
                    message="The requested context budget exceeds configured Discover limits.",
                    reason=f"{field} must be between 1 and {maximum}.",
                    field=f"budget.{field}",
                    accepted=f"A positive value not greater than {maximum}.",
                    corrective_actions=(f"Lower budget.{field} to {maximum} or less.",),
                )

    @staticmethod
    def _module_candidates(
        index: PythonProjectIndexResult,
        terms: tuple[str, ...],
    ) -> tuple[_ModuleCandidate, ...]:
        candidates = []
        for record in index.modules:
            score = score_named_candidate(
                identifier=record.name,
                name=record.name.rsplit(".", 1)[-1],
                path=record.path,
                kind="module",
                terms=terms,
            )
            candidates.append(
                _ModuleCandidate(
                    record=record,
                    score=score.score,
                    matched_terms=score.matched_terms,
                )
            )
        return tuple(
            sorted(
                candidates,
                key=lambda item: relevance_sort_key(
                    item.score,
                    item.record.name,
                    item.record.path,
                ),
            )
        )

    @staticmethod
    def _symbol_candidates(
        index: PythonProjectIndexResult,
        terms: tuple[str, ...],
        symbol_atlas: tuple[Any, ...] = (),
    ) -> tuple[_SymbolCandidate, ...]:
        candidates: list[_SymbolCandidate] = []
        seen: set[tuple[str, str, int]] = set()
        for record in index.symbols:
            score = score_named_candidate(
                identifier=record.qualified_name,
                name=record.name,
                path=record.path,
                kind=record.kind,
                terms=terms,
            )
            candidates.append(
                _SymbolCandidate(
                    record=record,
                    score=score.score,
                    matched_terms=score.matched_terms,
                )
            )
            seen.add((record.qualified_name, record.path, record.line))
        for item in symbol_atlas:
            if not isinstance(item, dict) or item.get("provider") == "python_ast":
                continue
            try:
                record = PythonSymbolRecord(
                    qualified_name=str(item["qualified_name"]),
                    module=str(item.get("module") or item.get("path") or "semantic"),
                    name=str(item["name"]),
                    kind=str(item["kind"]),
                    path=str(item["path"]),
                    line=int(item.get("line", 1)),
                    end_line=(None if item.get("end_line") is None else int(item["end_line"])),
                )
            except (KeyError, TypeError, ValueError):
                continue
            identity = (record.qualified_name, record.path, record.line)
            if identity in seen:
                continue
            score = score_named_candidate(
                identifier=record.qualified_name,
                name=record.name,
                path=record.path,
                kind=record.kind,
                terms=terms,
            )
            candidates.append(
                _SymbolCandidate(
                    record=record,
                    score=score.score,
                    matched_terms=score.matched_terms,
                    provider=str(item.get("provider", "semantic")),
                    provenance=(
                        "inferred"
                        if item.get("classification") == "semantic"
                        else "conventional"
                        if item.get("classification") == "heuristic"
                        else "parser_confirmed"
                    ),
                )
            )
            seen.add(identity)
        return tuple(
            sorted(
                candidates,
                key=lambda item: relevance_sort_key(
                    item.score,
                    item.record.qualified_name,
                    item.record.path,
                    str(item.record.line),
                ),
            )
        )

    @staticmethod
    def _file_candidates(
        snapshot: RepositorySnapshot,
        terms: tuple[str, ...],
        changed_paths: set[str],
        modules: tuple[_ModuleCandidate, ...],
        symbols: tuple[_SymbolCandidate, ...],
    ) -> tuple[_FileCandidate, ...]:
        module_boost: dict[str, int] = {}
        module_terms: dict[str, tuple[str, ...]] = {}
        for item in modules:
            module_boost[item.record.path] = max(
                module_boost.get(item.record.path, 0),
                item.score,
            )
            module_terms[item.record.path] = _merge_terms(
                terms,
                module_terms.get(item.record.path, ()),
                item.matched_terms,
            )
        symbol_boost: dict[str, int] = {}
        symbol_terms: dict[str, tuple[str, ...]] = {}
        for item in symbols:
            symbol_boost[item.record.path] = max(
                symbol_boost.get(item.record.path, 0),
                item.score,
            )
            symbol_terms[item.record.path] = _merge_terms(
                terms,
                symbol_terms.get(item.record.path, ()),
                item.matched_terms,
            )

        candidates = []
        for record in snapshot.files:
            category = _context_category(record)
            path_score = score_path_candidate(
                record.label,
                category=category,
                terms=terms,
                git_changed=record.label in changed_paths,
            )
            score = path_score.score
            score += module_boost.get(record.label, 0) // 2
            score += symbol_boost.get(record.label, 0) // 2
            matched = _merge_terms(
                terms,
                path_score.matched_terms,
                module_terms.get(record.label, ()),
                symbol_terms.get(record.label, ()),
            )
            candidates.append(
                _FileCandidate(
                    record=record,
                    category=category,
                    score=score,
                    matched_terms=matched,
                    git_changed=path_score.git_changed,
                )
            )
        return tuple(
            sorted(
                candidates,
                key=lambda item: relevance_sort_key(
                    item.score,
                    item.record.label,
                ),
            )
        )

    @staticmethod
    def _relationship_candidates(
        index: PythonProjectIndexResult,
        terms: tuple[str, ...],
        selected_identifiers: set[str],
        selected_paths: set[str],
        relationship_atlas: tuple[Any, ...] = (),
    ) -> tuple[_RelationshipCandidate, ...]:
        del index
        candidates: list[_RelationshipCandidate] = []
        for item in relationship_atlas:
            if not isinstance(item, dict):
                continue
            evidence = item.get("source_evidence", {})
            if not isinstance(evidence, dict):
                continue
            try:
                kind = str(item["type"])
                source = str(item["source"])
                target = str(item["target"])
                path = str(evidence["path"])
                line = int(evidence.get("line", 1))
            except (KeyError, TypeError, ValueError):
                continue
            if kind not in {"import", "call", "inheritance"}:
                continue
            score = score_relationship_candidate(
                kind=kind,
                source=source,
                target=target,
                path=path,
                terms=terms,
                selected=selected_identifiers,
            )
            if path not in selected_paths and not score.connected:
                continue
            candidates.append(
                _RelationshipCandidate(
                    kind=kind,
                    source=source,
                    target=target,
                    path=path,
                    line=line,
                    score=score.score,
                    confidence=str(item.get("confidence", "medium")),
                    provider=str(item.get("provider", "project_intelligence")),
                    provenance=(
                        "inferred"
                        if item.get("classification") == "semantic"
                        else "conventional"
                        if item.get("classification") == "heuristic"
                        else "parser_confirmed"
                    ),
                )
            )
        return tuple(
            sorted(
                candidates,
                key=lambda item: relevance_sort_key(
                    item.score,
                    item.kind,
                    item.source,
                    item.target,
                    item.path,
                    str(item.line),
                ),
            )
        )

    @staticmethod
    def _symbol_focus(
        symbols: Iterable[_SymbolCandidate],
    ) -> dict[str, tuple[int, ...]]:
        result: dict[str, list[int]] = {}
        for item in symbols:
            result.setdefault(item.record.path, []).append(item.record.line)
        return {
            path: tuple(lines)
            for path, lines in sorted(result.items(), key=lambda item: item[0].casefold())
        }

    @staticmethod
    def _initial_excerpt_limit(budget: CodeContextBudget, files: int) -> int:
        if files < 1:
            return _MIN_EXCERPT_CHARS
        reserved = min(1_600, budget.max_chars // 2)
        available = max(_MIN_EXCERPT_CHARS, budget.max_chars - reserved)
        return min(_MAX_INITIAL_EXCERPT_CHARS, max(_MIN_EXCERPT_CHARS, available // files))

    @staticmethod
    def _unknowns(
        *,
        snapshot: RepositorySnapshot,
        python_index: PythonProjectIndexResult,
        git: GitSummary,
        selected_files: list[ContextFile],
        unreadable_files: int,
    ) -> tuple[ContextUnknown, ...]:
        unknowns = [
            ContextUnknown(
                code="REMOTE_CONTEXT_UNAVAILABLE",
                reason="No approved remote evidence provider is configured for this context slice.",
            )
        ]
        if not python_index.modules:
            unknowns.append(
                ContextUnknown(
                    code="SEMANTIC_CONTEXT_UNAVAILABLE",
                    reason="No supported Python modules were available for bounded AST context.",
                )
            )
        elif python_index.truncated or python_index.diagnostics:
            unknowns.append(
                ContextUnknown(
                    code="SEMANTIC_CONTEXT_PARTIAL",
                    reason="Python AST context is partial because parsing or configured limits omitted evidence.",
                )
            )
        if not git.available:
            unknowns.append(
                ContextUnknown(
                    code="GIT_CONTEXT_UNAVAILABLE",
                    reason=(
                        str(git.diagnostics[0].get("message"))
                        if git.diagnostics
                        else "Local Git context is unavailable."
                    ),
                )
            )
        if unreadable_files:
            unknowns.append(
                ContextUnknown(
                    code="SELECTED_FILE_CONTEXT_UNAVAILABLE",
                    reason=f"{unreadable_files} selected file(s) could not be read safely.",
                )
            )
        if not selected_files:
            unknowns.append(
                ContextUnknown(
                    code="NO_RELEVANT_FILE_CONTEXT",
                    reason="No relevant readable files were retained for the task.",
                )
            )
        if snapshot.truncated:
            unknowns.append(
                ContextUnknown(
                    code="REPOSITORY_CONTEXT_PARTIAL",
                    reason="Repository traversal reached one or more configured limits.",
                )
            )
        return tuple(sorted(unknowns, key=lambda item: (item.code, item.reason)))

    def _compact_response(
        self,
        *,
        project: ProjectIdentity,
        request: GetCodeContextRequest,
        terms: tuple[str, ...],
        files: list[ContextFile],
        modules: list[ContextModule],
        symbols: list[ContextSymbol],
        relationships: list[ContextRelationship],
        git: dict[str, Any],
        providers: dict[str, Any],
        unknowns: tuple[ContextUnknown, ...],
        reasons: set[str],
        total_files: int,
        total_symbols: int,
        total_relationships: int,
        unreadable_files: int,
        diagnostic_degradation: bool,
    ) -> GetCodeContextResponse:
        def build() -> GetCodeContextResponse:
            paths = {item.path for item in files}
            retained_modules = tuple(item for item in modules if item.path in paths)
            retained_symbols = tuple(item for item in symbols if item.path in paths)
            retained_relationships = tuple(
                item for item in relationships if item.path in paths
            )
            omissions = ContextOmissions(
                files=max(0, total_files - len(files)),
                symbols=max(0, total_symbols - len(retained_symbols)),
                relationships=max(
                    0,
                    total_relationships - len(retained_relationships),
                ),
                unreadable_files=unreadable_files,
            )
            active_reasons = set(reasons)
            truncated = bool(active_reasons)
            confidence = (
                Confidence.LOW
                if not files
                else Confidence.MEDIUM
                if truncated or diagnostic_degradation
                else Confidence.HIGH
            )
            active_unknowns = list(unknowns)
            if not files and not any(
                item.code == "NO_RELEVANT_FILE_CONTEXT" for item in active_unknowns
            ):
                active_unknowns.append(
                    ContextUnknown(
                        code="NO_RELEVANT_FILE_CONTEXT",
                        reason="No relevant readable files were retained for the task.",
                    )
                )
            active_unknowns.sort(key=lambda item: (item.code, item.reason))
            response = GetCodeContextResponse(
                project=project,
                task=request.task,
                budget=request.budget,
                task_terms=terms,
                files=tuple(files),
                modules=retained_modules,
                symbols=retained_symbols,
                relationships=retained_relationships,
                instructions=tuple(
                    item.path for item in files if item.category == "instruction"
                ),
                tests=tuple(item.path for item in files if item.category == "test"),
                contracts=tuple(
                    item.path for item in files if item.category == "contract"
                ),
                git=git,
                providers=providers,
                unknowns=tuple(active_unknowns),
                omissions=omissions,
                confidence=confidence,
                truncated=truncated,
                truncation_reasons=tuple(sorted(active_reasons)),
                fingerprint="0" * 64,
            )
            payload = response.to_json_dict()
            payload.pop("fingerprint")
            return replace(response, fingerprint=stable_fingerprint(payload))

        response = build()
        if _serialized_length(response) <= request.budget.max_chars:
            return response

        reasons.add("max_chars")
        while True:
            shrinkable = [
                (index, item)
                for index, item in enumerate(files)
                if len(item.excerpt) > _MIN_EXCERPT_CHARS
            ]
            if shrinkable:
                index, item = max(
                    shrinkable,
                    key=lambda pair: (len(pair[1].excerpt), pair[1].path.casefold(), pair[1].path),
                )
                target = max(_MIN_EXCERPT_CHARS, len(item.excerpt) // 2)
                excerpt = item.excerpt[:target].rstrip() or item.excerpt[:target]
                files[index] = replace(
                    item,
                    excerpt=excerpt,
                    end_line=item.start_line + excerpt.count("\n"),
                    truncated=True,
                )
            elif relationships:
                relationships.pop()
            elif symbols:
                symbols.pop()
            elif modules:
                modules.pop()
            elif len(files) > 1:
                removed = files.pop()
                modules[:] = [item for item in modules if item.path != removed.path]
                symbols[:] = [item for item in symbols if item.path != removed.path]
                relationships[:] = [
                    item for item in relationships if item.path != removed.path
                ]
            elif files:
                removed = files.pop()
                modules[:] = [item for item in modules if item.path != removed.path]
                symbols[:] = [item for item in symbols if item.path != removed.path]
                relationships[:] = [
                    item for item in relationships if item.path != removed.path
                ]
            else:
                response = build()
                if _serialized_length(response) <= request.budget.max_chars:
                    return response
                raise DiscoverError(
                    code="DISCOVER_CONTEXT_BUDGET_TOO_SMALL",
                    message="The context response cannot fit the requested character budget.",
                    reason="The minimum valid response exceeds budget.max_chars.",
                    field="budget.max_chars",
                    accepted="A larger explicit character budget within configured maxima.",
                    corrective_actions=("Increase budget.max_chars.",),
                )

            response = build()
            if _serialized_length(response) <= request.budget.max_chars:
                return response


def _context_category(record: ScannedFile) -> str:
    normalized = record.label.replace("\\", "/")
    lowered = normalized.casefold()
    parts = tuple(part for part in lowered.split("/") if part)
    name = parts[-1] if parts else lowered
    first = parts[0] if parts else ""
    if name in {"agents.md", "contributing.md", "codeowners"}:
        return "instruction"
    if first in {"policy", "policies"} or name.startswith("policy."):
        return "policy"
    if (
        first in {"contract", "contracts", "schema", "schemas"}
        or name.endswith(".schema.json")
        or name.startswith(("openapi.", "asyncapi."))
        or name.endswith((".graphql", ".gql", ".proto"))
    ):
        return "contract"
    if record.category == "test":
        return "test"
    if record.category == "documentation":
        return "documentation"
    if record.category == "configuration":
        return "configuration"
    if record.category == "source":
        return "source"
    return "other"


def _context_module(item: _ModuleCandidate) -> ContextModule:
    return ContextModule(
        name=item.record.name,
        path=item.record.path,
        relevance_score=item.score,
        matched_terms=item.matched_terms,
        provenance=ContextProvenance(
            kind="parser_confirmed",
            provider="python_ast",
            identifier=item.record.name,
        ),
    )


def _context_symbol(item: _SymbolCandidate) -> ContextSymbol:
    return ContextSymbol(
        qualified_name=item.record.qualified_name,
        module=item.record.module,
        name=item.record.name,
        kind=item.record.kind,
        path=item.record.path,
        line=item.record.line,
        end_line=item.record.end_line,
        relevance_score=item.score,
        matched_terms=item.matched_terms,
        provenance=ContextProvenance(
            kind=item.provenance,
            provider=item.provider,
            identifier=item.record.qualified_name,
        ),
    )


def _context_relationship(item: _RelationshipCandidate) -> ContextRelationship:
    return ContextRelationship(
        kind=item.kind,
        source=item.source,
        target=item.target,
        path=item.path,
        line=item.line,
        relevance_score=item.score,
        confidence=item.confidence,
        provenance=ContextProvenance(
            kind=item.provenance,
            provider=item.provider,
            identifier=f"{item.kind}:{item.source}:{item.target}:{item.path}:{item.line}",
        ),
    )


def _compact_git(
    git: GitSummary,
    local_changes: dict[str, Any],
    *,
    max_paths: int,
) -> dict[str, Any]:
    diagnostics = [
        {
            "code": str(item.get("code", "GIT_CONTEXT_DIAGNOSTIC")),
            "message": str(item.get("message", "Local Git context is degraded.")),
        }
        for item in git.diagnostics[:3]
    ]
    all_changed_paths = tuple(
        dict.fromkeys(
            str(item.get("path"))
            for item in local_changes.get("changes", [])
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        )
    )
    changed_paths = all_changed_paths[:max_paths]
    return {
        "available": git.available,
        "repository": git.repository,
        "branch": git.branch,
        "detached": git.detached,
        "head": git.head,
        "status": git.status,
        "remote": git.remote,
        "changed_paths": list(changed_paths),
        "omitted_changed_paths": max(0, len(all_changed_paths) - len(changed_paths)),
        "change_summary": dict(local_changes.get("summary", {})),
        "diagnostics": diagnostics,
        "truncated": bool(
            git.truncated
            or local_changes.get("truncated", False)
            or len(all_changed_paths) > len(changed_paths)
        ),
    }


def _extract_excerpt(
    content: str,
    *,
    terms: tuple[str, ...],
    focus_lines: tuple[int, ...],
    max_chars: int,
) -> tuple[str, int, int, bool]:
    lines = content.splitlines()
    if not lines:
        return "\n", 1, 1, False
    full = "\n".join(lines)
    if len(full) <= max_chars:
        return full, 1, len(lines), False

    focus = focus_lines[0] if focus_lines else _first_matching_line(lines, terms)
    index = max(0, min(len(lines) - 1, focus - 1))
    start = max(0, index - 4)
    end = min(len(lines), index + 9)
    excerpt = "\n".join(lines[start:end])
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rstrip() or excerpt[:max_chars]
    if not excerpt:
        excerpt = lines[index][:_MIN_EXCERPT_CHARS] or "\n"
    end_line = start + 1 + excerpt.count("\n")
    return excerpt, start + 1, end_line, True


def _first_matching_line(lines: list[str], terms: tuple[str, ...]) -> int:
    for index, line in enumerate(lines, start=1):
        lowered = line.casefold()
        if any(term in lowered for term in terms):
            return index
    return 1


def _merge_terms(
    ordered_terms: tuple[str, ...],
    *groups: tuple[str, ...],
) -> tuple[str, ...]:
    available = {item for group in groups for item in group}
    return tuple(term for term in ordered_terms if term in available)


def _serialized_length(response: GetCodeContextResponse) -> int:
    return len(
        json.dumps(
            response.to_json_dict(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )


__all__ = ["ContextBrokerService"]
