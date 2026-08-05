from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from .contracts import Confidence, VerificationDeclaration
from .errors import DiscoverError
from .impact_contracts import (
    ImpactBudget,
    ImpactDependant,
    ImpactOmissions,
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
    def __init__(self, *, boundary: Path, settings: DiscoverSettings) -> None:
        self._boundary = boundary
        self._settings = settings

    def inspect(self, request: InspectImpactRequest) -> InspectImpactResponse:
        self._validate_budget(request.budget)
        authority = ReadAuthority(self._boundary, self._settings)
        snapshot = RepositoryScanner(authority, self._settings).snapshot(request.project)
        index = PythonProjectIndexer(authority=authority, settings=self._settings).index(
            request.project, snapshot
        )
        verification = VerificationDiscoveryService(
            authority=authority,
            settings=self._settings,
        ).discover(request.project, snapshot)

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
        dependants_all = _dependants(
            changed_modules=changed_modules,
            changed_symbols=changed_symbol_records,
            imports=index.imports,
            calls=index.calls,
            inheritance=index.inheritance,
        )
        dependants = dependants_all[: request.budget.max_dependants]
        tests_all = _affected_tests(
            snapshot=snapshot,
            changed_paths=changed,
            changed_modules=changed_modules,
            changed_symbols=changed_symbol_records,
            dependants=dependants_all,
        )
        tests = tests_all[: request.budget.max_tests]
        verification_all = tuple(
            _handoff(item, request.changed_paths)
            for item in verification.declarations
            if _verification_applicable(item, request.changed_paths)
        )
        handoffs = verification_all[: request.budget.max_verifications]

        omissions = ImpactOmissions(
            symbols=max(0, len(all_changed_symbols) - len(changed_symbols)),
            dependants=max(0, len(dependants_all) - len(dependants)),
            tests=max(0, len(tests_all) - len(tests)),
            verifications=max(0, len(verification_all) - len(handoffs)),
        )
        reasons = set(index.truncation_reasons)
        if snapshot.truncated:
            reasons.update(snapshot.truncation_reasons)
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
        )
        confidence = (
            Confidence.LOW
            if not index.modules
            else Confidence.MEDIUM
            if reasons or index.diagnostics or verification.diagnostics
            else Confidence.HIGH
        )
        response = InspectImpactResponse(
            project=snapshot.project,
            changed_paths=request.changed_paths,
            changed_symbols=changed_symbols,
            dependants=dependants,
            affected_tests=tests,
            verification_handoffs=handoffs,
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


def _affected_tests(*, snapshot, changed_paths, changed_modules, changed_symbols, dependants):
    targets = {
        *changed_modules,
        *(item.name for item in changed_symbols),
        *(item.qualified_name for item in changed_symbols),
    }
    dependant_paths = {item.path for item in dependants}
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
            reason = "The test contains an AST-confirmed dependant relationship."
            provenance = "python_ast"
            confidence = Confidence.HIGH
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


def _unknowns(*, request, changed_modules, changed_symbols, index_status, index_has_modules, verification_truncated):
    values: list[ImpactUnknown] = []
    unsupported = tuple(path for path in request.changed_paths if not path.casefold().endswith(".py"))
    if unsupported:
        values.append(
            ImpactUnknown(
                code="NON_PYTHON_SYMBOL_IMPACT_UNAVAILABLE",
                reason="Symbol-level impact is currently limited to Python; non-Python paths retain path and verification evidence only.",
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
    return tuple(sorted(values, key=lambda item: (item.code, item.reason)))


def _path_category(path: str) -> str:
    lowered = path.casefold().replace("\\", "/")
    name = lowered.rsplit("/", 1)[-1]
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
    payload = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = ["ImpactGraphService"]
