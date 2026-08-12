from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from .analyzers import AnalysisContext, AnalyzerRegistry, run_pipeline
from .analyzers.architecture import ArchitectureComponentsAnalyzer
from .analyzers.change_impact import ChangeImpactAnalyzer
from .analyzers.dependencies import DependencyImportsAnalyzer
from .analyzers.repository_map import RepositoryMapAnalyzer
from .contracts import Confidence, VerificationDeclaration
from .errors import DiscoverError
from .intelligence import ProjectIntelligenceService
from .impact_contracts import (
    ImpactBudget,
    ImpactDependant,
    ImpactImplementationStep,
    ImpactOmissions,
    ImpactRelationship,
    ImpactSymbol,
    ImpactTest,
    ImpactUnknown,
    ImpactVerificationHandoff,
    InspectImpactRequest,
    InspectImpactResponse,
)
from .python_index import PythonProjectIndexer, PythonSymbolRecord
from .read_authority import ReadAuthority
from .scanner import RepositoryScanner
from .settings import DiscoverSettings
from .verification import VerificationDiscoveryService


class ImpactGraphService:
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

    def inspect(self, request: InspectImpactRequest) -> InspectImpactResponse:
        self._validate_budget(request.budget)
        intelligence = self._intelligence.get(request.project)
        authority = ReadAuthority(self._boundary, self._settings)
        snapshot = intelligence.snapshot
        index = intelligence.python_index
        verification = VerificationDiscoveryService(
            authority=authority,
            settings=self._settings,
        ).discover(request.project, snapshot)
        analysis = run_pipeline(
            (
                "repository.map",
                "architecture.components",
                "dependencies.imports",
                "change.impact",
            ),
            AnalysisContext(
                snapshot=snapshot,
                authority=authority,
                project_path=request.project,
                python_index=index,
                verification=verification.declarations,
                changed_paths=request.changed_paths,
                analyzer_options={
                    "architecture.components": {
                        "max_components": self._settings.limits.max_directories,
                    },
                    "dependencies.imports": {
                        "max_edges": self._settings.limits.python_max_records,
                    },
                    "change.impact": {
                        "max_impacts": self._settings.limits.python_max_records,
                    },
                },
            ),
            AnalyzerRegistry(
                (
                    RepositoryMapAnalyzer(),
                    ArchitectureComponentsAnalyzer(),
                    DependencyImportsAnalyzer(),
                    ChangeImpactAnalyzer(),
                )
            ),
        )
        change_analysis = analysis.outputs["change.impact"]

        changed = frozenset(request.changed_paths)
        changed_modules = {
            item.name: item.path for item in index.modules if item.path in changed
        }
        all_changed_symbols = tuple(
            _impact_symbol(item) for item in index.symbols if item.path in changed
        )
        changed_symbols = all_changed_symbols[: request.budget.max_symbols]
        changed_symbol_records = tuple(
            item for item in index.symbols if item.path in changed
        )
        python_dependants = _dependants(
            changed_modules=changed_modules,
            changed_symbols=changed_symbol_records,
            imports=index.imports,
            calls=index.calls,
            inheritance=index.inheritance,
        )
        python_transitive_dependants = _transitive_import_dependants(
            changed_modules=changed_modules,
            imports=index.imports,
        )
        javascript_dependants = _javascript_dependants(change_analysis)
        dependants_all = _merge_dependants(
            python_dependants,
            python_transitive_dependants,
            javascript_dependants,
        )
        dependants = dependants_all[: request.budget.max_dependants]
        semantic_relationships = _semantic_relationship_impacts(
            relationship_graph=intelligence.relationship_graph,
            symbol_atlas=intelligence.symbol_atlas,
            changed_paths=changed,
        )
        tests_all = _affected_tests(
            snapshot=snapshot,
            changed_paths=changed,
            changed_modules=changed_modules,
            changed_symbols=changed_symbol_records,
            dependants=dependants_all,
            relationship_paths={item.source_path for item in semantic_relationships},
        )
        tests = tests_all[: request.budget.max_tests]
        verification_all = tuple(
            _handoff(item, request.changed_paths)
            for item in verification.declarations
            if _verification_applicable(item, request.changed_paths)
        )
        handoffs = verification_all[: request.budget.max_verifications]
        relationships_all = _merge_relationship_impacts(
            semantic_relationships,
            _relationship_impacts(
                snapshot=snapshot,
                changed_paths=request.changed_paths,
                task_terms=request.task_terms,
            ),
        )
        remaining_relationship_budget = max(
            0,
            request.budget.max_dependants - len(dependants),
        )
        relationship_impacts = relationships_all[:remaining_relationship_budget]
        task_term_matches = _task_term_matches(
            request.task_terms,
            request.changed_paths,
            changed_symbols,
            dependants,
            tests,
        )
        implementation_steps = _implementation_steps(
            changed_paths=request.changed_paths,
            relationships=relationship_impacts,
            tests=tests,
            handoffs=handoffs,
        )

        omissions = ImpactOmissions(
            symbols=max(0, len(all_changed_symbols) - len(changed_symbols)),
            dependants=(
                max(0, len(dependants_all) - len(dependants))
                + max(0, len(relationships_all) - len(relationship_impacts))
            ),
            tests=max(0, len(tests_all) - len(tests)),
            verifications=max(0, len(verification_all) - len(handoffs)),
        )
        reasons = set(index.truncation_reasons)
        if snapshot.truncated:
            reasons.update(snapshot.truncation_reasons)
        if analysis.truncated:
            reasons.add("dependency_analysis")
        if omissions.symbols:
            reasons.add("max_symbols")
        if omissions.dependants:
            reasons.add("max_dependants")
        if omissions.tests:
            reasons.add("max_tests")
        if omissions.verifications:
            reasons.add("max_verifications")

        unknowns = _unknowns(
            request=request,
            changed_modules=changed_modules,
            changed_symbols=changed_symbol_records,
            index_status=index.status,
            index_has_modules=bool(index.modules),
            verification_truncated=verification.truncated,
            analysis_unknowns=analysis.unknowns,
            task_terms_available=bool(request.task_terms),
        )
        confidence = (
            Confidence.LOW
            if not index.modules and not dependants_all
            else Confidence.MEDIUM
            if not index.modules
            or reasons
            or index.diagnostics
            or verification.diagnostics
            or analysis.diagnostics
            else Confidence.HIGH
        )
        response = InspectImpactResponse(
            project=snapshot.project,
            changed_paths=request.changed_paths,
            changed_symbols=changed_symbols,
            dependants=dependants,
            relationship_impacts=relationship_impacts,
            task_term_matches=task_term_matches,
            affected_tests=tests,
            verification_handoffs=handoffs,
            implementation_steps=implementation_steps,
            unknowns=unknowns,
            omissions=omissions,
            confidence=confidence,
            truncated=bool(reasons),
            truncation_reasons=tuple(sorted(reasons)),
            fingerprint="0" * 64,
        )
        payload = response.to_json_dict()
        payload.pop("fingerprint")
        return replace(response, fingerprint=_fingerprint(payload))

    def _validate_budget(self, budget: ImpactBudget) -> None:
        maxima = {
            "max_symbols": self._settings.limits.python_max_records,
            "max_dependants": self._settings.limits.python_max_records,
            "max_tests": self._settings.limits.max_files,
            "max_verifications": self._settings.limits.max_evidence,
        }
        for name, maximum in maxima.items():
            if getattr(budget, name) > maximum:
                raise DiscoverError(
                    code="DISCOVER_IMPACT_BUDGET_INVALID",
                    message="The requested impact budget exceeds configured Discover limits.",
                    reason=f"{name} must not exceed {maximum}.",
                    field=f"budget.{name}",
                    accepted=f"A positive integer not greater than {maximum}.",
                    corrective_actions=(f"Lower budget.{name}.",),
                )


def _impact_symbol(item: PythonSymbolRecord) -> ImpactSymbol:
    return ImpactSymbol(
        qualified_name=item.qualified_name,
        module=item.module,
        name=item.name,
        kind=item.kind,
        path=item.path,
        line=item.line,
    )


def _dependants(*, changed_modules, changed_symbols, imports, calls, inheritance):
    records: dict[tuple[str, str, str, str, int], ImpactDependant] = {}
    module_names = frozenset(changed_modules)
    symbol_names = {item.name: item.qualified_name for item in changed_symbols}
    class_names = {
        item.name: item.qualified_name for item in changed_symbols if item.kind == "class"
    }

    for item in imports:
        target = next(
            (
                name
                for name in module_names
                if item.target_module == name or item.target_module.startswith(f"{name}.")
            ),
            None,
        )
        if target is None or item.source_module in module_names:
            continue
        record = ImpactDependant(
            kind="import",
            source=item.source_module,
            target=target,
            path=item.path,
            line=item.line,
            confidence=Confidence.HIGH,
        )
        records[(record.kind, record.source, record.target, record.path, record.line)] = record

    for item in calls:
        callee = item.callee.rsplit(".", 1)[-1]
        target = symbol_names.get(callee)
        if target is None or item.caller == target:
            continue
        record = ImpactDependant(
            kind="call",
            source=item.caller,
            target=target,
            path=item.path,
            line=item.line,
            confidence=Confidence.HIGH,
        )
        records[(record.kind, record.source, record.target, record.path, record.line)] = record

    for item in inheritance:
        base = item.base.rsplit(".", 1)[-1]
        target = class_names.get(base)
        if target is None or item.symbol == target:
            continue
        record = ImpactDependant(
            kind="inheritance",
            source=item.symbol,
            target=target,
            path=item.path,
            line=item.line,
            confidence=Confidence.HIGH,
        )
        records[(record.kind, record.source, record.target, record.path, record.line)] = record

    return tuple(
        sorted(
            records.values(),
            key=lambda item: (
                item.kind,
                item.source.casefold(),
                item.source,
                item.target.casefold(),
                item.target,
                item.path.casefold(),
                item.path,
                item.line,
            ),
        )
    )


def _transitive_import_dependants(*, changed_modules, imports, max_depth: int = 2):
    """Return bounded reverse-import evidence beyond the direct dependant layer."""
    if max_depth < 2 or not changed_modules:
        return ()
    results: dict[tuple[str, str, str, int], ImpactDependant] = {}
    for root in sorted(changed_modules, key=lambda value: (value.casefold(), value)):
        frontier = {root}
        seen = {root}
        for depth in range(1, max_depth + 1):
            next_frontier: set[str] = set()
            for item in imports:
                if item.source_module in seen:
                    continue
                if not any(
                    item.target_module == target
                    or item.target_module.startswith(f"{target}.")
                    for target in frontier
                ):
                    continue
                seen.add(item.source_module)
                next_frontier.add(item.source_module)
                if depth < 2:
                    continue
                record = ImpactDependant(
                    kind="import",
                    source=item.source_module,
                    target=root,
                    path=item.path,
                    line=item.line,
                    confidence=Confidence.MEDIUM,
                    provenance="python_ast_transitive",
                )
                results[(record.source, record.target, record.path, record.line)] = record
            frontier = next_frontier
            if not frontier:
                break
    return tuple(
        sorted(
            results.values(),
            key=lambda item: (
                item.source.casefold(),
                item.source,
                item.target.casefold(),
                item.target,
                item.path.casefold(),
                item.path,
                item.line,
            ),
        )
    )


def _javascript_dependants(change_analysis) -> tuple[ImpactDependant, ...]:
    records: list[ImpactDependant] = []
    for item in change_analysis.facts.get("dependants", ()):
        if item.get("kind") != "javascript_import":
            continue
        depth = int(item.get("depth", 1))
        records.append(
            ImpactDependant(
                kind="import",
                source=str(item["source"]),
                target=str(item["target"]),
                path=str(item["source"]),
                line=int(item.get("line", 1)),
                confidence=Confidence.HIGH if depth == 1 else Confidence.MEDIUM,
                provenance=(
                    "javascript_static_import"
                    if depth == 1
                    else "javascript_static_import_transitive"
                ),
            )
        )
    return tuple(records)


def _merge_dependants(*groups: tuple[ImpactDependant, ...]) -> tuple[ImpactDependant, ...]:
    records: dict[tuple[str, str, str, str, int, str], ImpactDependant] = {}
    for group in groups:
        for item in group:
            key = (
                item.kind,
                item.source,
                item.target,
                item.path,
                item.line,
                item.provenance,
            )
            records.setdefault(key, item)
    values = tuple(records.values())
    direct = tuple(item for item in values if "transitive" not in item.provenance)
    transitive = tuple(item for item in values if "transitive" in item.provenance)
    return (*direct, *transitive)


def _affected_tests(
    *,
    snapshot,
    changed_paths,
    changed_modules,
    changed_symbols,
    dependants,
    relationship_paths: set[str] | None = None,
):
    targets = {
        *changed_modules,
        *(item.name for item in changed_symbols),
        *(item.qualified_name for item in changed_symbols),
    }
    dependant_paths = {item.path for item in dependants}
    semantic_paths = relationship_paths or set()
    changed_stems = {
        Path(path).stem.removeprefix("test_").removesuffix("_test").casefold()
        for path in changed_paths
    }
    symbol_terms = {item.name.casefold() for item in changed_symbols}
    results: list[ImpactTest] = []
    for record in snapshot.files:
        if record.category != "test":
            continue
        normalized = record.label.replace("\\", "/")
        matches: set[str] = set()
        reason = None
        provenance = None
        confidence = Confidence.MEDIUM
        if normalized in changed_paths:
            matches.add(normalized)
            reason = "The test file is directly changed."
            provenance = "observed"
            confidence = Confidence.HIGH
        if normalized in dependant_paths:
            matches.update(
                item.target for item in dependants if item.path == normalized
            )
            reason = "The test contains a deterministic parser-confirmed dependant relationship."
            provenance = "python_ast"
            confidence = Confidence.HIGH
        if normalized in semantic_paths and not matches:
            matches.add(normalized)
            reason = "The test contains a normalized semantic-provider reference to changed code."
            provenance = "semantic_provider"
            confidence = Confidence.MEDIUM
        tokens = _tokens(normalized)
        conventional = sorted(
            term
            for term in (*changed_stems, *symbol_terms)
            if term and term in tokens
        )
        if conventional and not matches:
            matches.update(conventional)
            reason = "The test name conventionally matches changed code evidence."
            provenance = "conventional"
        if matches and reason and provenance:
            results.append(
                ImpactTest(
                    path=normalized,
                    reason=reason,
                    confidence=confidence,
                    matched_targets=tuple(sorted(matches, key=str.casefold)),
                    provenance=provenance,
                )
            )
    return tuple(
        sorted(
            results,
            key=lambda item: (
                0 if item.confidence == Confidence.HIGH else 1,
                item.path.casefold(),
                item.path,
            ),
        )
    )


def _semantic_relationship_impacts(
    *,
    relationship_graph,
    symbol_atlas,
    changed_paths: frozenset[str],
) -> tuple[ImpactRelationship, ...]:
    changed_symbols: dict[str, str] = {}
    for item in symbol_atlas:
        if not isinstance(item, dict) or str(item.get("path", "")) not in changed_paths:
            continue
        path = str(item["path"])
        for key in ("qualified_name", "name"):
            value = str(item.get(key, "")).strip()
            if value:
                changed_symbols[value] = path
    records: dict[tuple[str, str], ImpactRelationship] = {}
    for edge in relationship_graph:
        if not isinstance(edge, dict) or edge.get("classification") != "semantic":
            continue
        evidence = edge.get("source_evidence")
        if not isinstance(evidence, dict):
            continue
        source_path = str(evidence.get("path", "")).replace("\\", "/")
        if not source_path or source_path in changed_paths:
            continue
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        target_path = next(
            (
                path
                for identifier, path in changed_symbols.items()
                if target == identifier
                or source == identifier
                or target.endswith(f"::{identifier}")
                or source.endswith(f"::{identifier}")
            ),
            None,
        )
        if target_path is None:
            continue
        records[(source_path, target_path)] = ImpactRelationship(
            kind="semantic_reference",
            source_path=source_path,
            target_path=target_path,
            reason="Normalized semantic-provider evidence references a changed symbol.",
            confidence=Confidence.MEDIUM,
            provenance="semantic_provider",
        )
    return tuple(
        sorted(
            records.values(),
            key=lambda item: (item.source_path.casefold(), item.target_path.casefold()),
        )
    )


def _merge_relationship_impacts(*groups: tuple[ImpactRelationship, ...]) -> tuple[ImpactRelationship, ...]:
    records: dict[tuple[str, str, str], ImpactRelationship] = {}
    for group in groups:
        for item in group:
            records.setdefault((item.kind, item.source_path, item.target_path), item)
    return tuple(
        sorted(
            records.values(),
            key=lambda item: (item.kind, item.source_path.casefold(), item.target_path.casefold()),
        )
    )


def _relationship_impacts(*, snapshot, changed_paths, task_terms) -> tuple[ImpactRelationship, ...]:
    records: dict[tuple[str, str, str], ImpactRelationship] = {}
    candidates = tuple(record.label.replace("\\", "/") for record in snapshot.files)
    support_categories = {"contract", "configuration", "documentation", "policy"}
    for changed in changed_paths:
        changed_category = _path_category(changed)
        stem_terms = _tokens(Path(changed).stem)
        for candidate in candidates:
            if candidate == changed:
                continue
            candidate_category = _path_category(candidate)
            if (
                candidate_category not in support_categories
                and changed_category not in support_categories
            ):
                continue
            overlap = stem_terms & _tokens(candidate)
            if not overlap:
                continue
            relationship_category = (
                candidate_category
                if candidate_category in support_categories
                else changed_category
            )
            kind = f"{relationship_category}_reference"
            record = ImpactRelationship(
                kind=kind,
                source_path=candidate,
                target_path=changed,
                reason=(
                    f"Path tokens relate {relationship_category} evidence to the changed path: "
                    f"{', '.join(sorted(overlap))}."
                ),
                confidence=Confidence.MEDIUM,
                provenance="path_token_reference",
            )
            records[(record.kind, record.source_path, record.target_path)] = record
    for term in task_terms:
        for candidate in (*changed_paths, *candidates):
            if term not in _tokens(candidate):
                continue
            record = ImpactRelationship(
                kind="task_term",
                source_path=candidate,
                target_path=term,
                reason=f"The supplied task term '{term}' matches repository path evidence.",
                confidence=Confidence.LOW,
                provenance="task_token_match",
            )
            records[(record.kind, record.source_path, record.target_path)] = record
    return tuple(sorted(records.values(), key=lambda item: (item.kind, item.source_path.casefold(), item.target_path.casefold())))


def _task_term_matches(task_terms, changed_paths, changed_symbols, dependants, tests) -> tuple[str, ...]:
    evidence = [*changed_paths]
    evidence.extend(item.qualified_name for item in changed_symbols)
    evidence.extend(item.source for item in dependants)
    evidence.extend(item.path for item in tests)
    return tuple(
        term
        for term in task_terms
        if any(term in _tokens(value) or term in value.casefold() for value in evidence)
    )


def _implementation_steps(*, changed_paths, relationships, tests, handoffs) -> tuple[ImpactImplementationStep, ...]:
    steps: list[ImpactImplementationStep] = []
    categories: dict[str, tuple[str, ...]] = {}
    for category in ("contract", "configuration", "documentation", "policy", "code"):
        paths = tuple(path for path in changed_paths if _path_category(path) == category)
        if paths:
            categories[category] = paths
    for category, paths in categories.items():
        related = tuple(
            item.source_path
            for item in relationships
            if item.target_path in paths and item.source_path not in paths
        )
        evidence = tuple(dict.fromkeys((*paths, *related)))
        steps.append(
            ImpactImplementationStep(
                step_id=f"impact-step-{category}",
                category=category,
                action={
                    "contract": "Update contract consumers and validate schema compatibility.",
                    "configuration": "Review configuration consumers and integration defaults.",
                    "documentation": "Reconcile documentation with the changed behavior.",
                    "policy": "Review policy-sensitive consumers without treating Discover evidence as policy authority.",
                    "code": "Implement the changed code paths and preserve bounded interfaces.",
                }[category],
                paths=paths,
                evidence=evidence,
                confidence=Confidence.MEDIUM if related else Confidence.LOW,
            )
        )
    if tests:
        steps.append(
            ImpactImplementationStep(
                step_id="impact-step-tests",
                category="test",
                action="Update or run the deterministically selected affected tests.",
                paths=tuple(item.path for item in tests),
                evidence=tuple(item.reason for item in tests),
                confidence=Confidence.HIGH if all(item.confidence == Confidence.HIGH for item in tests) else Confidence.MEDIUM,
            )
        )
    if handoffs:
        steps.append(
            ImpactImplementationStep(
                step_id="impact-step-verification",
                category="verification",
                action="Execute the non-mutating verification handoffs through Work after implementation.",
                paths=tuple(item.source_path for item in handoffs),
                evidence=tuple(item.verification_id for item in handoffs),
                confidence=Confidence.HIGH,
            )
        )
    return tuple(steps)


def _verification_applicable(item: VerificationDeclaration, changed_paths: tuple[str, ...]) -> bool:
    categories = {_path_category(path) for path in changed_paths}
    if item.category in {"repository_verification", "test", "lint", "typecheck"}:
        return True
    if item.category == "dependency" and "dependency" in categories:
        return True
    if item.category == "documentation" and "documentation" in categories:
        return True
    return item.source_path in changed_paths


def _handoff(item: VerificationDeclaration, changed_paths: tuple[str, ...]) -> ImpactVerificationHandoff:
    return ImpactVerificationHandoff(
        handoff_id=f"ho-impact-{item.id}",
        verification_id=item.id,
        category=item.category,
        reason="Changed evidence may require this discovered verification workflow.",
        profile=item.profile,
        arguments=item.arguments,
        source_path=item.source_path,
    )


def _unknowns(
    *,
    request,
    changed_modules,
    changed_symbols,
    index_status,
    index_has_modules,
    verification_truncated,
    analysis_unknowns,
    task_terms_available,
):
    del changed_modules
    values: list[ImpactUnknown] = []
    unsupported = tuple(
        path for path in request.changed_paths if not path.casefold().endswith(".py")
    )
    if unsupported:
        values.append(
            ImpactUnknown(
                code="NON_PYTHON_SYMBOL_IMPACT_UNAVAILABLE",
                reason="Symbol-level impact is currently limited to Python; supported JavaScript and TypeScript paths retain static dependency and verification evidence.",
            )
        )
    if not index_has_modules:
        values.append(
            ImpactUnknown(
                code="PYTHON_INDEX_UNAVAILABLE",
                reason="No supported Python modules were available for impact analysis.",
            )
        )
    elif index_status != "completed":
        values.append(
            ImpactUnknown(
                code="PYTHON_IMPACT_PARTIAL",
                reason="Python impact evidence is partial because parsing or configured limits omitted records.",
            )
        )
    if any(path.casefold().endswith(".py") for path in request.changed_paths) and not changed_symbols:
        values.append(
            ImpactUnknown(
                code="CHANGED_SYMBOLS_NOT_DECLARED",
                reason="No declared Python class or function symbols were found in the changed Python paths.",
            )
        )
    if verification_truncated:
        values.append(
            ImpactUnknown(
                code="VERIFICATION_INVENTORY_PARTIAL",
                reason="Additional verification declarations may exist beyond configured limits.",
            )
        )
    for reason in analysis_unknowns:
        lowered = reason.casefold()
        if "dynamic import" in lowered:
            code = "JAVASCRIPT_DYNAMIC_IMPORT_IMPACT_UNKNOWN"
        elif "could not be resolved" in lowered:
            code = "JAVASCRIPT_IMPORT_TARGET_UNRESOLVED"
        else:
            code = "DEPENDENCY_IMPACT_PARTIAL"
        values.append(ImpactUnknown(code=code, reason=reason))
    if not task_terms_available:
        values.append(
            ImpactUnknown(
                code="TASK_TOKEN_IMPACT_UNAVAILABLE",
                reason="No task terms were supplied to inspect_impact; task-token impact remains unevaluated rather than inferred.",
            )
        )
    unique = {(item.code, item.reason): item for item in values}
    return tuple(
        sorted(unique.values(), key=lambda item: (item.code, item.reason))
    )


def _path_category(path: str) -> str:
    lowered = path.casefold().replace("\\", "/")
    name = lowered.rsplit("/", 1)[-1]
    if lowered.startswith(("contracts/", "contract/", "schemas/", "schema/")) or name.endswith(".schema.json") or name.startswith(("openapi.", "asyncapi.")) or name.endswith((".proto", ".graphql", ".gql")):
        return "contract"
    if lowered.startswith(("policy/", "policies/")) or name.startswith("policy."):
        return "policy"
    if lowered.startswith(("settings/", "config/", "configs/", ".github/")) or name in {"pyproject.toml", "package.json", "tox.ini", "dockerfile", "makefile"} or name.endswith((".toml", ".yaml", ".yml", ".ini")):
        return "configuration"
    if name in {"uv.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}:
        return "dependency"
    if lowered.startswith(("docs/", "doc/")) or name.endswith((".md", ".rst")):
        return "documentation"
    return "code"


def _tokens(value: str) -> set[str]:
    normalized = value.casefold().replace("\\", "/")
    for marker in ("/", ".", "-", "_"):
        normalized = normalized.replace(marker, " ")
    return {item for item in normalized.split() if item and item not in {"test", "tests"}}


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = ["ImpactGraphService"]
