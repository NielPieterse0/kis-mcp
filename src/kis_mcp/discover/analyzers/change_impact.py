from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

from .contracts import AnalysisContext, AnalyzerOutput


class ChangeImpactAnalyzer:
    analyzer_id = "change.impact"

    def analyze(
        self,
        context: AnalysisContext,
        prior: Mapping[str, AnalyzerOutput],
    ) -> AnalyzerOutput:
        dependency_output = prior.get("dependencies.imports")
        if dependency_output is None:
            raise ValueError("change.impact requires dependencies.imports")
        maximum = _positive_option(
            context.options_for(self.analyzer_id).get("max_impacts", 1_000),
            "max_impacts",
        )
        dependencies = tuple(dependency_output.facts.get("dependencies", ()))
        dependants_all = _reverse_dependants(
            dependencies=dependencies,
            changed_paths=context.changed_paths,
        )
        dependants = dependants_all[:maximum]
        omitted = max(0, len(dependants_all) - len(dependants))
        deterministic_paths = {
            str(item["source"])
            for item in dependants_all
        }
        changed = frozenset(context.changed_paths)
        category_impact = tuple(
            sorted(
                (
                    {
                        "path": record.label,
                        "category": record.category,
                    }
                    for record in context.snapshot.files
                    if record.label in changed
                ),
                key=lambda item: (
                    str(item["path"]).casefold(),
                    str(item["path"]),
                ),
            )
        )
        heuristic_paths = tuple(
            sorted(
                (
                    {
                        "path": record.label,
                        "matched_terms": matched,
                        "confidence": "low",
                        "provenance": "task_token",
                    }
                    for record in context.snapshot.files
                    if record.label not in changed
                    and record.label not in deterministic_paths
                    and (
                        matched := tuple(
                            term
                            for term in context.task_terms
                            if term in _tokens(record.label)
                        )
                    )
                ),
                key=lambda item: (
                    str(item["path"]).casefold(),
                    str(item["path"]),
                ),
            )
        )
        unknowns = list(dependency_output.unknowns)
        if omitted:
            unknowns.append(
                f"{omitted} dependant impact record(s) were omitted by the configured limit."
            )
        return AnalyzerOutput(
            analyzer_id=self.analyzer_id,
            facts={
                "dependants": dependants,
                "category_impact": category_impact,
                "heuristic_paths": heuristic_paths,
            },
            diagnostics=dependency_output.diagnostics,
            unknowns=tuple(unknowns),
            truncated=dependency_output.truncated or omitted > 0,
        )


def _reverse_dependants(
    *,
    dependencies: tuple[Mapping[str, object], ...],
    changed_paths: tuple[str, ...],
) -> tuple[dict[str, object], ...]:
    reverse: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for edge in dependencies:
        source = edge.get("source")
        target = edge.get("target")
        if isinstance(source, str) and isinstance(target, str):
            reverse[target].append(edge)
    for edges in reverse.values():
        edges.sort(
            key=lambda item: (
                str(item.get("source", "")).casefold(),
                str(item.get("source", "")),
                str(item.get("kind", "")),
                int(item.get("line", 0)),
            )
        )

    records: dict[tuple[str, str, str, int], dict[str, object]] = {}
    for root in sorted(set(changed_paths), key=lambda value: (value.casefold(), value)):
        visited = {root}
        frontier = {root}
        depth = 1
        while frontier:
            next_frontier: set[str] = set()
            for target in sorted(frontier, key=lambda value: (value.casefold(), value)):
                for edge in reverse.get(target, ()):  # deterministic list
                    source = str(edge["source"])
                    if source in visited:
                        continue
                    visited.add(source)
                    next_frontier.add(source)
                    kind = str(edge.get("kind", "dependency"))
                    line = int(edge.get("line", 1))
                    record = {
                        "source": source,
                        "target": root,
                        "kind": kind,
                        "line": line,
                        "depth": depth,
                        "confidence": "high" if depth == 1 else "medium",
                        "provenance": (
                            "static_dependency"
                            if depth == 1
                            else "static_dependency_transitive"
                        ),
                    }
                    records[(source, root, kind, line)] = record
            frontier = next_frontier
            depth += 1

    return tuple(
        sorted(
            records.values(),
            key=lambda item: (
                int(item["depth"]),
                str(item["source"]).casefold(),
                str(item["source"]),
                str(item["target"]).casefold(),
                str(item["target"]),
                str(item["kind"]),
                int(item["line"]),
            ),
        )
    )


def _tokens(value: str) -> set[str]:
    normalized = value.casefold().replace("\\", "/")
    for marker in ("/", ".", "-", "_"):
        normalized = normalized.replace(marker, " ")
    return {item for item in normalized.split() if item}


def _positive_option(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


__all__ = ["ChangeImpactAnalyzer"]
