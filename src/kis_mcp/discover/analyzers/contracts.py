from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    snapshot: Any
    authority: Any
    project_path: str
    python_index: Any
    verification: tuple[Any, ...]
    changed_paths: tuple[str, ...]
    analyzer_options: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    task_terms: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.project_path, str) or not self.project_path.strip():
            raise ValueError("analysis project_path must be a non-empty string")
        if any(not isinstance(path, str) or not path.strip() for path in self.changed_paths):
            raise ValueError("analysis changed_paths must contain non-empty strings")
        if any(not isinstance(term, str) or not term.strip() for term in self.task_terms):
            raise ValueError("analysis task_terms must contain non-empty strings")
        object.__setattr__(
            self,
            "task_terms",
            tuple(dict.fromkeys(term.casefold() for term in self.task_terms)),
        )
        frozen = {
            str(analyzer_id): _freeze_mapping(options)
            for analyzer_id, options in self.analyzer_options.items()
        }
        object.__setattr__(self, "analyzer_options", MappingProxyType(frozen))

    def options_for(self, analyzer_id: str) -> Mapping[str, Any]:
        return self.analyzer_options.get(analyzer_id, MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class AnalyzerOutput:
    analyzer_id: str
    facts: Mapping[str, Any] = field(default_factory=dict)
    evidence: tuple[dict[str, Any], ...] = ()
    diagnostics: tuple[dict[str, Any], ...] = ()
    assumptions: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    truncated: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.analyzer_id, str) or not self.analyzer_id.strip():
            raise ValueError("analyzer_id must be a non-empty string")
        object.__setattr__(self, "facts", _freeze_mapping(self.facts))


class Analyzer(Protocol):
    analyzer_id: str

    def analyze(
        self,
        context: AnalysisContext,
        prior: Mapping[str, AnalyzerOutput],
    ) -> AnalyzerOutput: ...


__all__ = ["AnalysisContext", "Analyzer", "AnalyzerOutput"]
