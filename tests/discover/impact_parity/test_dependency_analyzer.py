from __future__ import annotations

from pathlib import Path

from kis_mcp.discover.analyzers import AnalysisContext, AnalyzerRegistry, run_pipeline
from kis_mcp.discover.analyzers.architecture import ArchitectureComponentsAnalyzer
from kis_mcp.discover.analyzers.dependencies import DependencyImportsAnalyzer
from kis_mcp.discover.analyzers.repository_map import RepositoryMapAnalyzer
from kis_mcp.discover.python_index import PythonProjectIndexer
from kis_mcp.discover.read_authority import ReadAuthority
from kis_mcp.discover.scanner import RepositoryScanner
from kis_mcp.discover.settings import DiscoverSettings


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")


def _context(
    root: Path,
    settings: DiscoverSettings,
    *,
    max_edges: int = 100,
) -> AnalysisContext:
    authority = ReadAuthority(root.parent, settings)
    snapshot = RepositoryScanner(authority, settings).snapshot(str(root))
    python_index = PythonProjectIndexer(
        authority=authority,
        settings=settings,
    ).index(str(root), snapshot)
    return AnalysisContext(
        snapshot=snapshot,
        authority=authority,
        project_path=str(root),
        python_index=python_index,
        verification=(),
        changed_paths=("src/pkg/service.py", "web/main.ts"),
        analyzer_options={
            "architecture.components": {"max_components": 100},
            "dependencies.imports": {
                "max_edges": max_edges,
                "javascript_extensions": (".ts",),
            },
        },
    )


def _registry() -> AnalyzerRegistry:
    return AnalyzerRegistry(
        (
            RepositoryMapAnalyzer(),
            ArchitectureComponentsAnalyzer(),
            DependencyImportsAnalyzer(),
        )
    )


def test_dependency_analyzer_resolves_local_python_and_typescript_imports(
    tmp_path: Path,
    discover_settings: DiscoverSettings,
) -> None:
    root = tmp_path / "fixture"
    root.mkdir()
    _write(
        root,
        {
            "src/pkg/__init__.py": "",
            "src/pkg/api.py": "from pkg import service\n",
            "src/pkg/service.py": "from pkg import repository\n",
            "src/pkg/repository.py": "VALUE = 1\n",
            "tests/test_service.py": "from pkg import service\n",
            "web/main.ts": (
                "import { service } from './service';\n"
                "export { feature } from './feature';\n"
                "const data = require('./data');\n"
                "const late = import('./lazy');\n"
            ),
            "web/service.ts": "export const service = 1;\n",
            "web/feature/index.ts": "export const feature = 1;\n",
            "web/data.ts": "export const data = 1;\n",
            "web/lazy.ts": "export const lazy = 1;\n",
        },
    )

    result = run_pipeline(
        ("repository.map", "architecture.components", "dependencies.imports"),
        _context(root, discover_settings),
        _registry(),
    )
    output = result.outputs["dependencies.imports"]

    assert output.facts["dependencies"] == (
        {
            "source": "src/pkg/api.py",
            "target": "src/pkg/service.py",
            "kind": "python_import",
            "line": 1,
        },
        {
            "source": "src/pkg/service.py",
            "target": "src/pkg/repository.py",
            "kind": "python_import",
            "line": 1,
        },
        {
            "source": "tests/test_service.py",
            "target": "src/pkg/service.py",
            "kind": "python_import",
            "line": 1,
        },
        {
            "source": "web/main.ts",
            "target": "web/data.ts",
            "kind": "javascript_import",
            "line": 3,
        },
        {
            "source": "web/main.ts",
            "target": "web/feature/index.ts",
            "kind": "javascript_import",
            "line": 2,
        },
        {
            "source": "web/main.ts",
            "target": "web/service.ts",
            "kind": "javascript_import",
            "line": 1,
        },
    )
    assert output.truncated is False
    assert any("dynamic import" in item.casefold() for item in output.unknowns)


def test_dependency_analyzer_bounds_edges_and_reports_omissions(
    tmp_path: Path,
    discover_settings: DiscoverSettings,
) -> None:
    root = tmp_path / "bounded"
    root.mkdir()
    _write(
        root,
        {
            "web/main.ts": (
                "import './a';\nimport './b';\nimport './c';\n"
            ),
            "web/a.ts": "export const a = 1;\n",
            "web/b.ts": "export const b = 1;\n",
            "web/c.ts": "export const c = 1;\n",
        },
    )

    output = run_pipeline(
        ("repository.map", "architecture.components", "dependencies.imports"),
        _context(root, discover_settings, max_edges=2),
        _registry(),
    ).outputs["dependencies.imports"]

    assert len(output.facts["dependencies"]) == 2
    assert output.truncated is True
    assert output.unknowns == (
        "1 local dependency edge(s) were omitted by the configured limit.",
    )
