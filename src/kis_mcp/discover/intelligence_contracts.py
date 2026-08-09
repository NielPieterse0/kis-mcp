from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import GitSummary, ProjectIdentity
from .python_index import PythonProjectIndexResult
from .scanner import RepositorySnapshot
from .semantic import SemanticEvidence


@dataclass(frozen=True, slots=True)
class ProjectIntelligenceRuntime:
    project: ProjectIdentity
    snapshot: RepositorySnapshot
    python_index: PythonProjectIndexResult
    git: GitSummary
    code_atlas: Mapping[str, Any]
    symbol_atlas: tuple[Mapping[str, Any], ...]
    relationship_graph: tuple[Mapping[str, Any], ...]
    semantic: SemanticEvidence
    persistence: Mapping[str, Any]
    source_fingerprint: str
    settings_fingerprint: str
    provider_fingerprint: str
    truncated: bool
    truncation_reasons: tuple[str, ...]


__all__ = ["ProjectIntelligenceRuntime"]
