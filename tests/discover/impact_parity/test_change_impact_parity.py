from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from kis_mcp.discover.analyzers import AnalysisContext, AnalyzerOutput
from kis_mcp.discover.analyzers.change_impact import ChangeImpactAnalyzer
from kis_mcp.discover.impact_contracts import ImpactBudget, InspectImpactRequest
from kis_mcp.discover.impact_graph import ImpactGraphService


def test_change_impact_analyzer_separates_deterministic_and_task_token_impact() -> None:
    snapshot = SimpleNamespace(
        files=(
            SimpleNamespace(label="web/core.ts", category="source"),
            SimpleNamespace(label="web/middle.ts", category="source"),
            SimpleNamespace(label="web/top.ts", category="source"),
            SimpleNamespace(label="tests/core.test.ts", category="test"),
            SimpleNamespace(label="src/billing/report.ts", category="source"),
            SimpleNamespace(label="config/app.json", category="configuration"),
        )
    )
    context = AnalysisContext(
        snapshot=snapshot,
        authority=object(),
        project_path=r"C:\Projects\fixture",
        python_index=SimpleNamespace(),
        verification=(),
        changed_paths=("web/core.ts", "config/app.json"),
        analyzer_options={"change.impact": {"max_impacts": 20}},
        task_terms=("billing",),
    )
    prior = {
        "dependencies.imports": AnalyzerOutput(
            analyzer_id="dependencies.imports",
            facts={
                "dependencies": (
                    {
                        "source": "web/middle.ts",
                        "target": "web/core.ts",
                        "kind": "javascript_import",
                        "line": 1,
                    },
                    {
                        "source": "web/top.ts",
                        "target": "web/middle.ts",
                        "kind": "javascript_import",
                        "line": 1,
                    },
                    {
                        "source": "tests/core.test.ts",
                        "target": "web/top.ts",
                        "kind": "javascript_import",
                        "line": 1,
                    },
                )
            },
        )
    }

    output = ChangeImpactAnalyzer().analyze(context, prior)

    assert output.facts["dependants"] == (
        {
            "source": "web/middle.ts",
            "target": "web/core.ts",
            "kind": "javascript_import",
            "line": 1,
            "depth": 1,
            "confidence": "high",
            "provenance": "static_dependency",
        },
        {
            "source": "web/top.ts",
            "target": "web/core.ts",
            "kind": "javascript_import",
            "line": 1,
            "depth": 2,
            "confidence": "medium",
            "provenance": "static_dependency_transitive",
        },
        {
            "source": "tests/core.test.ts",
            "target": "web/core.ts",
            "kind": "javascript_import",
            "line": 1,
            "depth": 3,
            "confidence": "medium",
            "provenance": "static_dependency_transitive",
        },
    )
    assert output.facts["category_impact"] == (
        {"path": "config/app.json", "category": "configuration"},
        {"path": "web/core.ts", "category": "source"},
    )
    assert output.facts["heuristic_paths"] == (
        {
            "path": "src/billing/report.ts",
            "matched_terms": ("billing",),
            "confidence": "low",
            "provenance": "task_token",
        },
    )


def test_impact_graph_adds_typescript_dependants_and_affected_tests(
    project_root: Path,
    discover_settings,
) -> None:
    files = {
        "web/core.ts": "export const core = 1;\n",
        "web/middle.ts": "import { core } from './core';\nexport { core };\n",
        "web/top.ts": "import { core } from './middle';\nexport { core };\n",
        "tests/core.test.ts": "import { core } from '../web/top';\n",
        "package.json": '{"name":"fixture","scripts":{"test":"vitest"}}',
    }
    for relative, content in files.items():
        target = project_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")

    response = ImpactGraphService(
        boundary=project_root.parent,
        settings=discover_settings,
    ).inspect(
        InspectImpactRequest(
            project=str(project_root),
            changed_paths=("web/core.ts",),
            budget=ImpactBudget(
                max_symbols=20,
                max_dependants=20,
                max_tests=20,
                max_verifications=20,
            ),
        )
    )

    javascript_dependants = tuple(
        item for item in response.dependants if item.provenance.startswith("javascript")
    )
    assert tuple((item.source, item.target) for item in javascript_dependants) == (
        ("web/middle.ts", "web/core.ts"),
        ("web/top.ts", "web/core.ts"),
        ("tests/core.test.ts", "web/core.ts"),
    )
    assert response.affected_tests[0].path == "tests/core.test.ts"
    assert response.affected_tests[0].confidence.value == "high"
    assert any(
        item.code == "TASK_TOKEN_IMPACT_UNAVAILABLE" for item in response.unknowns
    )
