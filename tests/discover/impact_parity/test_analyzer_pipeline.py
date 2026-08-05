from __future__ import annotations

from dataclasses import dataclass

import pytest

from kis_mcp.discover.analyzers import (
    AnalysisContext,
    AnalyzerOutput,
    AnalyzerRegistry,
    AnalyzerRegistryError,
    run_pipeline,
)


@dataclass(frozen=True)
class _Analyzer:
    analyzer_id: str
    unknown: str = "shared"
    truncated: bool = False

    def analyze(self, context: AnalysisContext, prior):
        if self.analyzer_id == "second":
            assert tuple(prior) == ("first",)
            with pytest.raises(TypeError):
                prior["illegal"] = AnalyzerOutput(analyzer_id="illegal")
            assert context.options_for("second") == {"limit": 2}
        return AnalyzerOutput(
            analyzer_id=self.analyzer_id,
            facts={"id": self.analyzer_id},
            unknowns=(self.unknown,),
            truncated=self.truncated,
        )


def _context() -> AnalysisContext:
    return AnalysisContext(
        snapshot=object(),
        authority=object(),
        project_path=r"C:\Projects\fixture",
        python_index=object(),
        verification=(),
        changed_paths=("src/a.py",),
        analyzer_options={"second": {"limit": 2}},
    )


def test_registry_is_deterministic_and_rejects_duplicate_or_unknown_ids() -> None:
    registry = AnalyzerRegistry((_Analyzer("second"), _Analyzer("first")))

    assert registry.identifiers() == ("first", "second")
    assert registry.resolve("first").analyzer_id == "first"

    with pytest.raises(AnalyzerRegistryError, match="Duplicate analyzer identifier"):
        registry.register(_Analyzer("first"))
    with pytest.raises(AnalyzerRegistryError, match="Unknown analyzer identifier"):
        registry.resolve("missing")


def test_pipeline_preserves_order_freezes_prior_and_deduplicates_unknowns() -> None:
    registry = AnalyzerRegistry(
        (_Analyzer("first", truncated=True), _Analyzer("second"))
    )

    result = run_pipeline(("first", "second"), _context(), registry)

    assert tuple(result.outputs) == ("first", "second")
    assert result.outputs["second"].facts == {"id": "second"}
    assert result.unknowns == ("shared",)
    assert result.truncated is True


def test_pipeline_rejects_analyzer_output_identity_mismatch() -> None:
    class Wrong:
        analyzer_id = "expected"

        def analyze(self, context, prior):
            return AnalyzerOutput(analyzer_id="different")

    registry = AnalyzerRegistry((Wrong(),))

    with pytest.raises(AnalyzerRegistryError, match="returned different"):
        run_pipeline(("expected",), _context(), registry)
