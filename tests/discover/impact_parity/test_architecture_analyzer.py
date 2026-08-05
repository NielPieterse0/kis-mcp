from __future__ import annotations

from kis_mcp.discover.analyzers import AnalysisContext, AnalyzerRegistry, run_pipeline
from kis_mcp.discover.analyzers.architecture import ArchitectureComponentsAnalyzer
from kis_mcp.discover.analyzers.repository_map import RepositoryMapAnalyzer
from kis_mcp.discover.contracts import ProjectIdentity
from kis_mcp.discover.scanner import RepositorySnapshot, ScannedFile


def _snapshot() -> RepositorySnapshot:
    project = ProjectIdentity(
        project_id="local:fixture",
        canonical_path=r"C:\Projects\fixture",
        repository_root=r"C:\Projects\fixture",
        git_root=None,
        remote_identity=None,
    )
    files = (
        ScannedFile("README.md", 10, ".md", "documentation"),
        ScannedFile("src/api/routes.py", 10, ".py", "source"),
        ScannedFile("src/api/service.py", 10, ".py", "source"),
        ScannedFile("src/core/model.py", 10, ".py", "source"),
        ScannedFile("packages/ui/index.ts", 10, ".ts", "source"),
        ScannedFile("services/jobs/worker.py", 10, ".py", "source"),
        ScannedFile("tests/test_api.py", 10, ".py", "test"),
    )
    return RepositorySnapshot(
        project=project,
        files=files,
        directories=("packages", "services", "src", "tests"),
        excluded_paths=(),
        total_bytes=70,
        visited_entries=11,
        truncated=False,
        truncation_reasons=(),
    )


def _context(max_components: int = 20) -> AnalysisContext:
    return AnalysisContext(
        snapshot=_snapshot(),
        authority=object(),
        project_path=r"C:\Projects\fixture",
        python_index=object(),
        verification=(),
        changed_paths=("src/api/service.py",),
        analyzer_options={"architecture.components": {"max_components": max_components}},
    )


def test_architecture_analyzer_groups_repository_units_deterministically() -> None:
    registry = AnalyzerRegistry((RepositoryMapAnalyzer(), ArchitectureComponentsAnalyzer()))

    result = run_pipeline(
        ("repository.map", "architecture.components"),
        _context(),
        registry,
    )

    assert tuple(
        item["path"] for item in result.outputs["repository.map"].facts["files"]
    ) == (
        "packages/ui/index.ts",
        "README.md",
        "services/jobs/worker.py",
        "src/api/routes.py",
        "src/api/service.py",
        "src/core/model.py",
        "tests/test_api.py",
    )
    assert result.outputs["architecture.components"].facts["components"] == (
        {"id": "component:.", "path": ".", "kind": "documentation", "files": 1},
        {"id": "component:packages/ui", "path": "packages/ui", "kind": "source", "files": 1},
        {"id": "component:services/jobs", "path": "services/jobs", "kind": "source", "files": 1},
        {"id": "component:src/api", "path": "src/api", "kind": "source", "files": 2},
        {"id": "component:src/core", "path": "src/core", "kind": "source", "files": 1},
        {"id": "component:tests", "path": "tests", "kind": "test", "files": 1},
    )


def test_architecture_analyzer_reports_deterministic_truncation() -> None:
    registry = AnalyzerRegistry((RepositoryMapAnalyzer(), ArchitectureComponentsAnalyzer()))

    result = run_pipeline(
        ("repository.map", "architecture.components"),
        _context(max_components=2),
        registry,
    )

    output = result.outputs["architecture.components"]
    assert tuple(item["path"] for item in output.facts["components"]) == (".", "packages/ui")
    assert output.truncated is True
    assert output.unknowns == (
        "4 architecture component(s) were omitted by the configured limit.",
    )
