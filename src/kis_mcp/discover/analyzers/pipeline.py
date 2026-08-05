from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .contracts import AnalysisContext, AnalyzerOutput
from .registry import AnalyzerRegistry, AnalyzerRegistryError


@dataclass(frozen=True, slots=True)
class PipelineResult:
    outputs: Mapping[str, AnalyzerOutput]
    evidence: tuple[dict[str, object], ...]
    diagnostics: tuple[dict[str, object], ...]
    assumptions: tuple[str, ...]
    unknowns: tuple[str, ...]
    truncated: bool


def run_pipeline(
    analyzer_ids: Iterable[str],
    context: AnalysisContext,
    registry: AnalyzerRegistry,
) -> PipelineResult:
    outputs: dict[str, AnalyzerOutput] = {}
    evidence: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    assumptions: list[str] = []
    unknowns: list[str] = []
    truncated = False

    for analyzer_id in analyzer_ids:
        analyzer = registry.resolve(analyzer_id)
        output = analyzer.analyze(context, MappingProxyType(dict(outputs)))
        if output.analyzer_id != analyzer_id:
            raise AnalyzerRegistryError(
                f"Analyzer {analyzer_id} returned {output.analyzer_id}"
            )
        if analyzer_id in outputs:
            raise AnalyzerRegistryError(f"Duplicate pipeline output: {analyzer_id}")
        outputs[analyzer_id] = output
        evidence.extend(output.evidence)
        diagnostics.extend(output.diagnostics)
        assumptions.extend(output.assumptions)
        unknowns.extend(output.unknowns)
        truncated = truncated or output.truncated

    return PipelineResult(
        outputs=MappingProxyType(dict(outputs)),
        evidence=tuple(evidence),
        diagnostics=tuple(diagnostics),
        assumptions=tuple(dict.fromkeys(assumptions)),
        unknowns=tuple(dict.fromkeys(unknowns)),
        truncated=truncated,
    )


__all__ = ["PipelineResult", "run_pipeline"]
