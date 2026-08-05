from __future__ import annotations

from collections.abc import Iterable

from .contracts import Analyzer


class AnalyzerRegistryError(ValueError):
    """Raised when analyzer registration or resolution is invalid."""


class AnalyzerRegistry:
    def __init__(self, analyzers: Iterable[Analyzer] = ()) -> None:
        self._analyzers: dict[str, Analyzer] = {}
        for analyzer in analyzers:
            self.register(analyzer)

    def register(self, analyzer: Analyzer) -> None:
        analyzer_id = analyzer.analyzer_id
        if not isinstance(analyzer_id, str) or not analyzer_id.strip():
            raise AnalyzerRegistryError("Analyzer identifier must be a non-empty string")
        if analyzer_id in self._analyzers:
            raise AnalyzerRegistryError(
                f"Duplicate analyzer identifier: {analyzer_id}"
            )
        self._analyzers[analyzer_id] = analyzer

    def resolve(self, analyzer_id: str) -> Analyzer:
        try:
            return self._analyzers[analyzer_id]
        except KeyError as exc:
            raise AnalyzerRegistryError(
                f"Unknown analyzer identifier: {analyzer_id}"
            ) from exc

    def identifiers(self) -> tuple[str, ...]:
        return tuple(sorted(self._analyzers, key=lambda value: (value.casefold(), value)))


__all__ = ["AnalyzerRegistry", "AnalyzerRegistryError"]
