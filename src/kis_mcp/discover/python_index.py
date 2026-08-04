from __future__ import annotations

import ast
from time import monotonic
from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any

from .contracts import ProjectDiagnostic, Severity
from .errors import DiscoverError
from .read_authority import ReadAuthority
from .scanner import RepositorySnapshot
from .settings import DiscoverSettings


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


@dataclass(frozen=True, slots=True)
class PythonModuleRecord:
    name: str
    path: str
    package: bool

    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json_value(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class PythonSymbolRecord:
    qualified_name: str
    module: str
    name: str
    kind: str
    path: str
    line: int
    end_line: int | None
    decorators: tuple[str, ...] = ()
    bases: tuple[str, ...] = ()

    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json_value(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class PythonImportRecord:
    source_module: str
    target_module: str
    imported_name: str | None
    alias: str | None
    level: int
    internal: bool
    path: str
    line: int

    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json_value(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class PythonInheritanceEdge:
    symbol: str
    base: str
    path: str
    line: int

    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json_value(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class PythonCallEdge:
    caller: str
    callee: str
    path: str
    line: int

    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json_value(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class PythonProjectIndexResult:
    status: str
    language: str
    modules: tuple[PythonModuleRecord, ...]
    symbols: tuple[PythonSymbolRecord, ...]
    imports: tuple[PythonImportRecord, ...]
    inheritance: tuple[PythonInheritanceEdge, ...]
    calls: tuple[PythonCallEdge, ...]
    diagnostics: tuple[ProjectDiagnostic, ...]
    summary: Mapping[str, int]
    truncated: bool
    truncation_reasons: tuple[str, ...]

    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json_value(getattr(self, field.name)) for field in fields(self)}


class _Collector(ast.NodeVisitor):
    def __init__(
        self,
        *,
        module: PythonModuleRecord,
        module_names: frozenset[str],
        symbols: list[PythonSymbolRecord],
        imports: list[PythonImportRecord],
        inheritance: list[PythonInheritanceEdge],
        calls: list[PythonCallEdge],
        diagnostics: list[ProjectDiagnostic],
        symbol_names: set[str],
        record_limit: int,
    ) -> None:
        self.module = module
        self.module_names = module_names
        self.symbols = symbols
        self.imports = imports
        self.inheritance = inheritance
        self.calls = calls
        self.diagnostics = diagnostics
        self.symbol_names = symbol_names
        self.record_limit = record_limit
        self.scope: list[tuple[str, str]] = []
        self.callables: list[str] = []
        self.truncated = False

    def _has_capacity(self) -> bool:
        total = (
            len(self.symbols)
            + len(self.imports)
            + len(self.inheritance)
            + len(self.calls)
        )
        if total < self.record_limit:
            return True
        self.truncated = True
        return False

    def _qualified(self, name: str) -> str:
        parts = [self.module.name, *(item[0] for item in self.scope), name]
        return ".".join(part for part in parts if part)

    def _add_symbol(
        self,
        node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
        kind: str,
        *,
        bases: tuple[str, ...] = (),
    ) -> str:
        qualified = self._qualified(node.name)
        if qualified in self.symbol_names:
            self.diagnostics.append(
                ProjectDiagnostic(
                    code="PY_DUPLICATE_SYMBOL",
                    message=f"Qualified symbol {qualified} is defined more than once.",
                    severity=Severity.WARNING,
                    path=self.module.path,
                )
            )
        else:
            self.symbol_names.add(qualified)
        if self._has_capacity():
            decorators = tuple(
                name
                for item in node.decorator_list
                if (name := _expr_name(item)) is not None
            )
            self.symbols.append(
                PythonSymbolRecord(
                    qualified_name=qualified,
                    module=self.module.name,
                    name=node.name,
                    kind=kind,
                    path=self.module.path,
                    line=node.lineno,
                    end_line=getattr(node, "end_lineno", None),
                    decorators=decorators,
                    bases=bases,
                )
            )
        return qualified

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = tuple(
            name for item in node.bases if (name := _expr_name(item)) is not None
        )
        qualified = self._add_symbol(node, "class", bases=bases)
        for base in bases:
            if self._has_capacity():
                self.inheritance.append(
                    PythonInheritanceEdge(
                        symbol=qualified,
                        base=base,
                        path=self.module.path,
                        line=node.lineno,
                    )
                )
        self.scope.append((node.name, "class"))
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        kind = "method" if self.scope and self.scope[-1][1] == "class" else "function"
        qualified = self._add_symbol(node, kind)
        self.scope.append((node.name, "callable"))
        self.callables.append(qualified)
        self.generic_visit(node)
        self.callables.pop()
        self.scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        kind = (
            "async_method"
            if self.scope and self.scope[-1][1] == "class"
            else "async_function"
        )
        qualified = self._add_symbol(node, kind)
        self.scope.append((node.name, "callable"))
        self.callables.append(qualified)
        self.generic_visit(node)
        self.callables.pop()
        self.scope.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if self.callables and self._has_capacity():
            self.calls.append(
                PythonCallEdge(
                    caller=self.callables[-1],
                    callee=_expr_name(node.func) or "unknown",
                    path=self.module.path,
                    line=node.lineno,
                )
            )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if not self._has_capacity():
                break
            target = alias.name
            self.imports.append(
                PythonImportRecord(
                    source_module=self.module.name,
                    target_module=target,
                    imported_name=None,
                    alias=alias.asname,
                    level=0,
                    internal=_internal_module(target, self.module_names),
                    path=self.module.path,
                    line=node.lineno,
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        base = _resolve_relative_base(self.module, node.level, node.module)
        for alias in node.names:
            if not self._has_capacity():
                break
            child = f"{base}.{alias.name}" if base else alias.name
            target = child if child in self.module_names else base
            internal = _internal_module(target, self.module_names)
            self.imports.append(
                PythonImportRecord(
                    source_module=self.module.name,
                    target_module=target,
                    imported_name=alias.name,
                    alias=alias.asname,
                    level=node.level,
                    internal=internal,
                    path=self.module.path,
                    line=node.lineno,
                )
            )
            if node.level > 0 and not internal:
                self.diagnostics.append(
                    ProjectDiagnostic(
                        code="PY_RELATIVE_IMPORT_UNRESOLVED",
                        message="A relative import could not be resolved to an indexed module.",
                        severity=Severity.WARNING,
                        path=self.module.path,
                    )
                )


class PythonProjectIndexer:
    def __init__(
        self,
        *,
        authority: ReadAuthority,
        settings: DiscoverSettings,
    ) -> None:
        self._authority = authority
        self._settings = settings

    def index(
        self,
        project_path: str,
        snapshot: RepositorySnapshot,
    ) -> PythonProjectIndexResult:
        started = monotonic()
        deadline = started + self._settings.limits.traversal_timeout_seconds
        python_files = tuple(
            record for record in snapshot.files if record.suffix.casefold() == ".py"
        )
        modules = tuple(
            sorted(
                (
                    PythonModuleRecord(
                        name=module_name,
                        path=record.label,
                        package=package,
                    )
                    for record in python_files
                    for module_name, package in (_module_name(record.label),)
                ),
                key=lambda item: (item.name, item.path),
            )
        )
        module_names = frozenset(module.name for module in modules)
        symbols: list[PythonSymbolRecord] = []
        imports: list[PythonImportRecord] = []
        inheritance: list[PythonInheritanceEdge] = []
        calls: list[PythonCallEdge] = []
        diagnostics: list[ProjectDiagnostic] = []
        symbol_names: set[str] = set()
        nodes_seen = 0
        files_indexed = 0
        reasons = set(snapshot.truncation_reasons)

        for module in modules:
            if monotonic() >= deadline:
                reasons.add("python_duration")
                break
            try:
                text = self._authority.read_relative_text(
                    project_path,
                    module.path,
                    max_bytes=self._settings.limits.max_file_bytes,
                ).content
            except DiscoverError:
                diagnostics.append(
                    ProjectDiagnostic(
                        code="PROJECT_INDEX_SOURCE_SKIPPED",
                        message="One authorized Python source file could not be read.",
                        severity=Severity.WARNING,
                        path=module.path,
                    )
                )
                continue
            try:
                tree = ast.parse(text, filename=module.path)
            except SyntaxError as exc:
                diagnostics.append(
                    ProjectDiagnostic(
                        code="PY_SYNTAX_ERROR",
                        message=(exc.msg or "Invalid Python syntax.")[:300],
                        severity=Severity.ERROR,
                        path=module.path,
                    )
                )
                files_indexed += 1
                continue
            file_nodes = sum(1 for _ in ast.walk(tree))
            if nodes_seen + file_nodes > self._settings.limits.python_max_nodes:
                reasons.add("python_max_nodes")
                break
            nodes_seen += file_nodes
            collector = _Collector(
                module=module,
                module_names=module_names,
                symbols=symbols,
                imports=imports,
                inheritance=inheritance,
                calls=calls,
                diagnostics=diagnostics,
                symbol_names=symbol_names,
                record_limit=self._settings.limits.python_max_records,
            )
            collector.visit(tree)
            files_indexed += 1
            if collector.truncated:
                reasons.add("python_max_records")
                break

        diagnostics.extend(_cycle_diagnostics(imports, module_names))
        diagnostics.sort(key=lambda item: (item.code, (item.path or "").casefold(), item.message))
        diagnostics = diagnostics[: self._settings.limits.max_evidence]
        symbols.sort(key=lambda item: (item.qualified_name, item.path, item.line))
        imports.sort(
            key=lambda item: (
                item.source_module,
                item.target_module,
                item.imported_name or "",
                item.path,
                item.line,
            )
        )
        inheritance.sort(key=lambda item: (item.symbol, item.base, item.path, item.line))
        calls.sort(key=lambda item: (item.caller, item.callee, item.path, item.line))
        has_errors = any(item.severity == Severity.ERROR for item in diagnostics)
        truncated = bool(reasons)
        status = "partial" if truncated or has_errors else "completed"
        summary = {
            "files_considered": len(modules),
            "files_indexed": files_indexed,
            "modules": len(modules),
            "symbols": len(symbols),
            "imports": len(imports),
            "inheritance_edges": len(inheritance),
            "call_edges": len(calls),
            "diagnostics": len(diagnostics),
            "nodes_indexed": nodes_seen,
        }
        return PythonProjectIndexResult(
            status=status,
            language="python",
            modules=modules,
            symbols=tuple(symbols),
            imports=tuple(imports),
            inheritance=tuple(inheritance),
            calls=tuple(calls),
            diagnostics=tuple(diagnostics),
            summary=summary,
            truncated=truncated,
            truncation_reasons=tuple(sorted(reasons)),
        )


def _module_name(path: str) -> tuple[str, bool]:
    parts = path.replace("\\", "/").lstrip("/").split("/")
    if parts and parts[0].casefold() in {"src", "lib"}:
        parts = parts[1:]
    filename = parts[-1]
    stem = filename[:-3]
    package = stem == "__init__"
    module_parts = parts[:-1] if package else [*parts[:-1], stem]
    return ".".join(module_parts), package


def _expr_name(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _expr_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return _expr_name(node.func)
    if isinstance(node, ast.Subscript):
        return _expr_name(node.value)
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Tuple):
        values = [name for item in node.elts if (name := _expr_name(item))]
        return ", ".join(values)
    return node.__class__.__name__


def _resolve_relative_base(
    module: PythonModuleRecord,
    level: int,
    imported_module: str | None,
) -> str:
    if level == 0:
        return imported_module or ""
    module_parts = module.name.split(".") if module.name else []
    package_parts = module_parts if module.package else module_parts[:-1]
    remove = max(0, level - 1)
    base_parts = (
        []
        if remove > len(package_parts)
        else package_parts[: len(package_parts) - remove]
    )
    if imported_module:
        base_parts.extend(imported_module.split("."))
    return ".".join(base_parts)


def _internal_module(target: str, module_names: frozenset[str]) -> bool:
    if not target:
        return False
    return target in module_names or any(
        item.startswith(f"{target}.") for item in module_names
    )


def _cycle_diagnostics(
    imports: list[PythonImportRecord],
    module_names: frozenset[str],
) -> list[ProjectDiagnostic]:
    graph = {name: set() for name in module_names}
    paths: dict[str, str] = {}
    for item in imports:
        paths.setdefault(item.source_module, item.path)
        if item.internal and item.target_module in graph:
            graph[item.source_module].add(item.target_module)

    reverse_graph = {name: set() for name in module_names}
    for source, targets in graph.items():
        for target in targets:
            reverse_graph[target].add(source)

    visited: set[str] = set()
    finish_order: list[str] = []
    for root in sorted(graph):
        if root in visited:
            continue
        frames: list[tuple[str, bool]] = [(root, False)]
        while frames:
            node, expanded = frames.pop()
            if expanded:
                finish_order.append(node)
                continue
            if node in visited:
                continue
            visited.add(node)
            frames.append((node, True))
            for neighbor in reversed(sorted(graph[node])):
                if neighbor not in visited:
                    frames.append((neighbor, False))

    assigned: set[str] = set()
    components: list[tuple[str, ...]] = []
    for root in reversed(finish_order):
        if root in assigned:
            continue
        component: list[str] = []
        pending = [root]
        assigned.add(root)
        while pending:
            node = pending.pop()
            component.append(node)
            for neighbor in reversed(sorted(reverse_graph[node])):
                if neighbor not in assigned:
                    assigned.add(neighbor)
                    pending.append(neighbor)
        ordered = tuple(sorted(component))
        if len(ordered) > 1 or root in graph[root]:
            components.append(ordered)

    return [
        ProjectDiagnostic(
            code="PY_IMPORT_CYCLE",
            message="Internal import cycle detected: " + " -> ".join(component),
            severity=Severity.WARNING,
            path=paths.get(component[0]),
        )
        for component in sorted(components)
    ]


__all__ = [
    "PythonCallEdge",
    "PythonImportRecord",
    "PythonInheritanceEdge",
    "PythonModuleRecord",
    "PythonProjectIndexResult",
    "PythonProjectIndexer",
    "PythonSymbolRecord",
]
