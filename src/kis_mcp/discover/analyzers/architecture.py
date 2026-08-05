from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from pathlib import PurePosixPath

from .contracts import AnalysisContext, AnalyzerOutput

_KIND_ORDER = {
    "configuration": 0,
    "source": 1,
    "test": 2,
    "documentation": 3,
    "generated": 4,
}


class ArchitectureComponentsAnalyzer:
    analyzer_id = "architecture.components"

    def analyze(
        self,
        context: AnalysisContext,
        prior: Mapping[str, AnalyzerOutput],
    ) -> AnalyzerOutput:
        if "repository.map" not in prior:
            raise ValueError("architecture.components requires repository.map")
        maximum = _positive_option(
            context.options_for(self.analyzer_id).get("max_components", 200),
            "max_components",
        )
        grouped: dict[str, list[str]] = {}
        categories: dict[str, Counter[str]] = {}
        for record in context.snapshot.files:
            component = _component_path(record.label)
            grouped.setdefault(component, []).append(record.label)
            categories.setdefault(component, Counter())[record.category] += 1

        paths = sorted(grouped, key=lambda value: (value.casefold(), value))
        selected = paths[:maximum]
        components = tuple(
            {
                "id": f"component:{path}",
                "path": path,
                "kind": _component_kind(categories[path]),
                "files": len(grouped[path]),
            }
            for path in selected
        )
        omitted = max(0, len(paths) - len(selected))
        return AnalyzerOutput(
            analyzer_id=self.analyzer_id,
            facts={"components": components},
            evidence=tuple(
                {
                    "kind": "component",
                    "location": item["path"],
                    "summary": f"Detected {item['kind']} component.",
                    "details": {"id": item["id"], "files": item["files"]},
                }
                for item in components
            ),
            unknowns=(
                f"{omitted} architecture component(s) were omitted by the configured limit.",
            )
            if omitted
            else (),
            truncated=omitted > 0,
        )


def _component_path(relative: str) -> str:
    parts = PurePosixPath(relative).parts
    if len(parts) == 1:
        return "."
    first = parts[0]
    if first.casefold() in {"src", "packages", "services", "apps"} and len(parts) >= 2:
        return f"{first}/{parts[1]}"
    return first


def _component_kind(counts: Counter[str]) -> str:
    return min(
        counts,
        key=lambda kind: (
            -counts[kind],
            _KIND_ORDER.get(kind, 99),
            kind.casefold(),
            kind,
        ),
    )


def _positive_option(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


__all__ = ["ArchitectureComponentsAnalyzer"]
