from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SemanticSymbol:
    qualified_name: str
    name: str
    kind: str
    path: str
    line: int
    end_line: int | None = None
    language: str = "unknown"


@dataclass(frozen=True, slots=True)
class SemanticRelationship:
    kind: str
    source: str
    target: str
    path: str
    line: int = 1


@dataclass(frozen=True, slots=True)
class SemanticEvidence:
    provider_id: str
    provider_version: str
    status: str
    symbols: tuple[SemanticSymbol, ...] = ()
    relationships: tuple[SemanticRelationship, ...] = ()
    unknowns: tuple[str, ...] = ()


class SemanticEvidenceProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    @property
    def provider_version(self) -> str: ...

    def read(
        self,
        project_path: str,
        source_paths: tuple[str, ...] = (),
    ) -> SemanticEvidence: ...


class NullSemanticProvider:
    provider_id = "none"
    provider_version = "0"

    def read(
        self,
        project_path: str,
        source_paths: tuple[str, ...] = (),
    ) -> SemanticEvidence:
        del project_path, source_paths
        return SemanticEvidence(
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            status="unavailable",
            unknowns=("Optional semantic provider is unavailable; deterministic local analysis is active.",),
        )


__all__ = [
    "NullSemanticProvider",
    "SemanticEvidence",
    "SemanticEvidenceProvider",
    "SemanticRelationship",
    "SemanticSymbol",
]
