from __future__ import annotations

import posixpath
import re
from collections.abc import Mapping
from pathlib import PurePosixPath

from ..errors import DiscoverError
from .contracts import AnalysisContext, AnalyzerOutput

_STATIC_MODULE_PATTERN = re.compile(
    r"\b(?:import|export)\s+(?:[^\"']*?\s+from\s+)?[\"']([^\"']+)[\"']"
)
_REQUIRE_PATTERN = re.compile(
    r"\brequire\s*\(\s*[\"']([^\"']+)[\"']\s*\)"
)
_DYNAMIC_IMPORT_PATTERN = re.compile(r"\bimport\s*\(")
_DEFAULT_JAVASCRIPT_EXTENSIONS = (
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".mts",
    ".cts",
)


class DependencyImportsAnalyzer:
    analyzer_id = "dependencies.imports"

    def analyze(
        self,
        context: AnalysisContext,
        prior: Mapping[str, AnalyzerOutput],
    ) -> AnalyzerOutput:
        if "architecture.components" not in prior:
            raise ValueError("dependencies.imports requires architecture.components")
        options = context.options_for(self.analyzer_id)
        maximum = _positive_option(options.get("max_edges", 1_000), "max_edges")
        extensions = _string_tuple(
            options.get("javascript_extensions", _DEFAULT_JAVASCRIPT_EXTENSIONS)
        )

        edges: dict[tuple[str, str, str, int], dict[str, object]] = {}
        diagnostics: list[dict[str, object]] = []
        unknowns: list[str] = []
        module_paths = {
            item.name: item.path for item in context.python_index.modules
        }
        for item in context.python_index.imports:
            if not item.internal:
                continue
            target = _nearest_python_module(item.target_module, module_paths)
            source = module_paths.get(item.source_module)
            if source is None or target is None or source == target:
                continue
            edge = {
                "source": source,
                "target": target,
                "kind": "python_import",
                "line": item.line,
            }
            edges[(source, target, "python_import", item.line)] = edge

        labels = {
            record.label: record
            for record in context.snapshot.files
        }
        javascript_paths = tuple(
            sorted(
                (
                    record.label
                    for record in context.snapshot.files
                    if record.suffix.casefold() in extensions
                ),
                key=lambda value: (value.casefold(), value),
            )
        )
        dynamic_paths: list[str] = []
        unresolved: set[tuple[str, str]] = set()
        for source in javascript_paths:
            try:
                content = context.authority.read_relative_text(
                    context.project_path,
                    source,
                    max_bytes=context.authority.settings.limits.max_file_bytes,
                ).content
            except DiscoverError as exc:
                diagnostics.append(
                    {
                        "code": "JAVASCRIPT_DEPENDENCY_SOURCE_SKIPPED",
                        "message": "A JavaScript or TypeScript source file could not be read safely.",
                        "path": source,
                        "reason": exc.code,
                    }
                )
                continue
            for line_number, line in enumerate(content.splitlines(), start=1):
                if _DYNAMIC_IMPORT_PATTERN.search(line):
                    dynamic_paths.append(source)
                specifiers = [
                    *(_STATIC_MODULE_PATTERN.findall(line)),
                    *(_REQUIRE_PATTERN.findall(line)),
                ]
                for specifier in specifiers:
                    if not specifier.startswith("."):
                        continue
                    target = _resolve_javascript(
                        source,
                        specifier,
                        labels,
                        extensions,
                    )
                    if target is None:
                        unresolved.add((source, specifier))
                        continue
                    edge = {
                        "source": source,
                        "target": target,
                        "kind": "javascript_import",
                        "line": line_number,
                    }
                    edges[(source, target, "javascript_import", line_number)] = edge

        ordered = tuple(
            sorted(
                edges.values(),
                key=lambda item: (
                    str(item["source"]).casefold(),
                    str(item["source"]),
                    str(item["target"]).casefold(),
                    str(item["target"]),
                    str(item["kind"]),
                    int(item["line"]),
                ),
            )
        )
        selected = ordered[:maximum]
        omitted = max(0, len(ordered) - len(selected))
        if dynamic_paths:
            unknowns.append(
                "Dynamic import targets were not treated as deterministic dependency edges: "
                + ", ".join(sorted(set(dynamic_paths), key=str.casefold))
                + "."
            )
        if unresolved:
            unknowns.append(
                f"{len(unresolved)} relative JavaScript or TypeScript import target(s) could not be resolved locally."
            )
        if omitted:
            unknowns.append(
                f"{omitted} local dependency edge(s) were omitted by the configured limit."
            )
        return AnalyzerOutput(
            analyzer_id=self.analyzer_id,
            facts={"dependencies": selected},
            diagnostics=tuple(
                sorted(
                    diagnostics,
                    key=lambda item: (
                        str(item.get("code", "")),
                        str(item.get("path", "")).casefold(),
                    ),
                )
            ),
            unknowns=tuple(unknowns),
            truncated=omitted > 0,
        )


def _nearest_python_module(
    target: str,
    module_paths: Mapping[str, str],
) -> str | None:
    candidate = target
    while candidate:
        path = module_paths.get(candidate)
        if path is not None:
            return path
        candidate = candidate.rpartition(".")[0]
    return None


def _resolve_javascript(
    source: str,
    specifier: str,
    files: Mapping[str, object],
    extensions: tuple[str, ...],
) -> str | None:
    if not specifier.startswith("."):
        return None
    source_parent = PurePosixPath(source).parent.as_posix()
    combined = posixpath.normpath(posixpath.join(source_parent, specifier))
    if combined == ".." or combined.startswith("../") or combined.startswith("/"):
        return None
    suffix = PurePosixPath(combined).suffix.casefold()
    candidates: list[str] = []
    if suffix in extensions:
        candidates.append(combined)
    else:
        candidates.extend(f"{combined}{extension}" for extension in extensions)
        candidates.extend(
            f"{combined}/index{extension}" for extension in extensions
        )
    return next((candidate for candidate in candidates if candidate in files), None)


def _positive_option(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or not value:
        raise ValueError("javascript_extensions must be a non-empty sequence")
    items = tuple(value)
    if any(
        not isinstance(item, str)
        or not item.startswith(".")
        or len(item) < 2
        for item in items
    ):
        raise ValueError(
            "javascript_extensions must contain non-empty dotted suffixes"
        )
    return tuple(dict.fromkeys(item.casefold() for item in items))


__all__ = [
    "DependencyImportsAnalyzer",
    "_nearest_python_module",
    "_resolve_javascript",
]
