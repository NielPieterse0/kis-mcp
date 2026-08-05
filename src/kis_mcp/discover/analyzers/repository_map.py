from __future__ import annotations

from collections.abc import Mapping

from .contracts import AnalysisContext, AnalyzerOutput


class RepositoryMapAnalyzer:
    analyzer_id = "repository.map"

    def analyze(
        self,
        context: AnalysisContext,
        prior: Mapping[str, AnalyzerOutput],
    ) -> AnalyzerOutput:
        del prior
        files = tuple(
            {
                "path": record.label,
                "category": record.category,
                "size": record.size,
                "suffix": record.suffix,
            }
            for record in sorted(
                context.snapshot.files,
                key=lambda item: (item.label.casefold(), item.label),
            )
        )
        return AnalyzerOutput(
            analyzer_id=self.analyzer_id,
            facts={
                "files": files,
                "directories": tuple(context.snapshot.directories),
            },
            truncated=context.snapshot.truncated,
            unknowns=tuple(
                f"Repository map is partial because of {reason}."
                for reason in context.snapshot.truncation_reasons
            ),
        )


__all__ = ["RepositoryMapAnalyzer"]
