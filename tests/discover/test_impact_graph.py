from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.discover.errors import DiscoverError
from kis_mcp.discover.contracts import Confidence
from kis_mcp.discover.impact_contracts import ImpactBudget, ImpactDependant, InspectImpactRequest
from kis_mcp.discover.impact_graph import ImpactGraphService, _merge_dependants
from kis_mcp.discover.intelligence import ProjectIntelligenceService
from kis_mcp.discover.semantic import SemanticEvidence, SemanticRelationship, SemanticSymbol

ROOT = Path(__file__).resolve().parents[2]


def _write_python_fixture(root: Path) -> None:
    src = root / "src"
    tests = root / "tests"
    src.mkdir()
    tests.mkdir()
    (src / "core.py").write_text(
        "class ChangedBase:\n    pass\n\n"
        "def changed(value):\n    return value + 1\n",
        encoding="utf-8",
    )
    (src / "consumer.py").write_text(
        "from .core import ChangedBase, changed\n\n"
        "class Child(ChangedBase):\n    pass\n\n"
        "def use_changed(value):\n    return changed(value)\n",
        encoding="utf-8",
    )
    (tests / "test_core.py").write_text(
        "from core import changed\n\n"
        "def test_changed():\n    assert changed(1) == 2\n",
        encoding="utf-8",
    )
    (tests / "test_unrelated.py").write_text(
        "def test_unrelated():\n    assert True\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        "[project]\nname='fixture'\nversion='0.1.0'\n\n[tool.pytest.ini_options]\naddopts='-q'\n",
        encoding="utf-8",
    )
    scripts = root / "scripts"
    scripts.mkdir()
    (scripts / "verify.ps1").write_text("Write-Output 'verify'\n", encoding="utf-8")


def _budget(**overrides: int) -> ImpactBudget:
    values = {
        "max_symbols": 20,
        "max_dependants": 20,
        "max_tests": 10,
        "max_verifications": 10,
    }
    values.update(overrides)
    return ImpactBudget(**values)


def _service(project_root: Path, discover_settings) -> ImpactGraphService:
    return ImpactGraphService(boundary=project_root.parent, settings=discover_settings)


def test_impact_graph_maps_symbols_dependants_tests_and_verifications(
    project_root: Path,
    discover_settings,
) -> None:
    _write_python_fixture(project_root)
    response = _service(project_root, discover_settings).inspect(
        InspectImpactRequest(
            project=str(project_root),
            changed_paths=("src/core.py",),
            budget=_budget(),
        )
    )

    assert {item.name for item in response.changed_symbols} == {"ChangedBase", "changed"}
    assert {(item.kind, item.source, item.target) for item in response.dependants}.issuperset(
        {
            ("import", "consumer", "core"),
            ("call", "consumer.use_changed", "core.changed"),
            ("inheritance", "consumer.Child", "core.ChangedBase"),
        }
    )
    assert response.affected_tests[0].path == "tests/test_core.py"
    assert response.affected_tests[0].confidence.value == "high"
    assert {item.verification_id for item in response.verification_handoffs}.issuperset(
        {"python-pytest", "powershell-verify-script"}
    )
    assert all(item.execution_available is False for item in response.verification_handoffs)
    assert response.confidence.value == "high"


def test_non_python_change_keeps_verification_and_reports_symbol_unknown(
    project_root: Path,
    discover_settings,
) -> None:
    (project_root / "README.md").write_text("# Docs\n", encoding="utf-8")
    response = _service(project_root, discover_settings).inspect(
        InspectImpactRequest(
            project=str(project_root),
            changed_paths=("README.md",),
            budget=_budget(),
        )
    )

    assert response.changed_symbols == ()
    assert any(
        item.code == "NON_PYTHON_SYMBOL_IMPACT_UNAVAILABLE" for item in response.unknowns
    )


def test_budgets_truncate_deterministically(project_root: Path, discover_settings) -> None:
    _write_python_fixture(project_root)
    request = InspectImpactRequest(
        project=str(project_root),
        changed_paths=("src/core.py",),
        budget=_budget(max_symbols=1, max_dependants=1, max_tests=1, max_verifications=1),
    )
    service = _service(project_root, discover_settings)

    first = service.inspect(request)
    second = service.inspect(request)

    assert first.to_json_dict() == second.to_json_dict()
    assert first.truncated is True
    assert first.omissions.symbols == 1
    assert first.omissions.dependants >= 2
    assert {"max_symbols", "max_dependants", "max_verifications"}.issubset(
        first.truncation_reasons
    )


def test_relationship_evidence_shares_the_dependant_budget(
    project_root: Path,
    discover_settings,
) -> None:
    contracts = project_root / "contracts"
    src = project_root / "src"
    docs = project_root / "docs"
    contracts.mkdir()
    src.mkdir()
    docs.mkdir()
    (contracts / "api.schema.json").write_text("{}\n", encoding="utf-8")
    (src / "api_client.py").write_text("VALUE = 1\n", encoding="utf-8")
    (docs / "api.md").write_text("# API\n", encoding="utf-8")

    response = _service(project_root, discover_settings).inspect(
        InspectImpactRequest(
            project=str(project_root),
            changed_paths=("contracts/api.schema.json",),
            task_terms=("api",),
            budget=_budget(max_dependants=1),
        )
    )

    assert len(response.dependants) + len(response.relationship_impacts) <= 1
    assert response.omissions.dependants >= 1
    assert "max_dependants" in response.truncation_reasons


def test_budget_is_rejected_before_project_resolution(project_root: Path, discover_settings) -> None:
    constrained = replace(
        discover_settings,
        limits=replace(discover_settings.limits, max_evidence=2),
    )
    request = InspectImpactRequest(
        project=str(project_root / "missing"),
        changed_paths=("src/core.py",),
        budget=_budget(max_verifications=3),
    )

    with pytest.raises(DiscoverError) as error:
        ImpactGraphService(boundary=project_root.parent, settings=constrained).inspect(request)

    assert error.value.code == "DISCOVER_IMPACT_BUDGET_INVALID"
    assert error.value.field == "budget.max_verifications"


def test_response_matches_checked_in_schema(project_root: Path, discover_settings) -> None:
    _write_python_fixture(project_root)
    response = _service(project_root, discover_settings).inspect(
        InspectImpactRequest(
            project=str(project_root),
            changed_paths=("src/core.py",),
            budget=_budget(),
        )
    )
    schema = json.loads(
        (ROOT / "contracts" / "discover" / "inspect-impact-response.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert list(Draft202012Validator(schema).iter_errors(response.to_json_dict())) == []


class _SemanticImpactProvider:
    provider_id = "semantic-test"
    provider_version = "1"
    state_fingerprint = "semantic-test-1"

    def read(self, project_path: str, source_paths: tuple[str, ...] = ()) -> SemanticEvidence:
        del project_path, source_paths
        return SemanticEvidence(
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            status="ready",
            symbols=(
                SemanticSymbol(
                    qualified_name="src/core.py::ChangedBase",
                    name="ChangedBase",
                    kind="class",
                    path="src/core.py",
                    line=1,
                    language="python",
                ),
            ),
            relationships=(
                SemanticRelationship(
                    kind="reference",
                    source="semantic_probe",
                    target="src/core.py::ChangedBase",
                    path="tests/semantic_probe.py",
                    line=3,
                ),
            ),
        )


def test_semantic_relationship_selects_affected_test_without_naming_convention(
    project_root: Path,
    discover_settings,
) -> None:
    _write_python_fixture(project_root)
    (project_root / "tests" / "semantic_probe.py").write_text(
        "def verify_reference():\n    assert True\n",
        encoding="utf-8",
    )
    intelligence = ProjectIntelligenceService(
        boundary=project_root.parent,
        settings=discover_settings,
        semantic_provider=_SemanticImpactProvider(),
    )
    response = ImpactGraphService(
        boundary=project_root.parent,
        settings=discover_settings,
        intelligence_service=intelligence,
    ).inspect(
        InspectImpactRequest(
            project=str(project_root),
            changed_paths=("src/core.py",),
            budget=_budget(),
        )
    )

    assert any(
        item.kind == "semantic_reference"
        and item.source_path == "tests/semantic_probe.py"
        for item in response.relationship_impacts
    )
    selected = next(item for item in response.affected_tests if item.path == "tests/semantic_probe.py")
    assert selected.provenance == "semantic_provider"
    assert selected.confidence.value == "medium"


def test_python_import_impact_includes_bounded_transitive_dependants(
    project_root: Path,
    discover_settings,
) -> None:
    _write_python_fixture(project_root)
    (project_root / "src" / "outer.py").write_text(
        "from .consumer import use_changed\n\ndef outer(value):\n    return use_changed(value)\n",
        encoding="utf-8",
    )

    response = _service(project_root, discover_settings).inspect(
        InspectImpactRequest(
            project=str(project_root),
            changed_paths=("src/core.py",),
            budget=_budget(),
        )
    )

    transitive = [item for item in response.dependants if item.provenance == "python_ast_transitive"]
    assert len(transitive) == 1
    assert transitive[0].source == "outer"
    assert transitive[0].target == "core"
    assert transitive[0].path == "src/outer.py"
    assert transitive[0].confidence.value == "medium"


def test_code_change_links_relevant_support_surfaces_with_explicit_provenance(
    project_root: Path,
    discover_settings,
) -> None:
    _write_python_fixture(project_root)
    for directory, name, content in (
        ("docs", "core.md", "# Core behavior\n"),
        ("settings", "core.json", "{}\n"),
        ("contracts", "core.schema.json", "{}\n"),
        ("policy", "core.json", "{}\n"),
    ):
        target = project_root / directory
        target.mkdir(exist_ok=True)
        (target / name).write_text(content, encoding="utf-8")

    response = _service(project_root, discover_settings).inspect(
        InspectImpactRequest(
            project=str(project_root),
            changed_paths=("src/core.py",),
            task_terms=("core",),
            budget=_budget(max_dependants=20),
        )
    )

    by_kind = {item.kind: item for item in response.relationship_impacts}
    assert by_kind["documentation_reference"].source_path == "docs/core.md"
    assert by_kind["configuration_reference"].source_path == "settings/core.json"
    assert by_kind["contract_reference"].source_path == "contracts/core.schema.json"
    assert by_kind["policy_reference"].source_path == "policy/core.json"
    assert all(
        item.provenance == "path_token_reference"
        for kind, item in by_kind.items()
        if kind.endswith("_reference") and kind != "semantic_reference"
    )


def test_direct_cross_language_dependants_precede_transitive_evidence_under_tight_budget() -> None:
    direct_python = ImpactDependant(
        kind="import",
        source="consumer",
        target="core",
        path="src/consumer.py",
        line=1,
        confidence=Confidence.HIGH,
        provenance="python_ast",
    )
    transitive_python = ImpactDependant(
        kind="import",
        source="outer",
        target="core",
        path="src/outer.py",
        line=1,
        confidence=Confidence.MEDIUM,
        provenance="python_ast_transitive",
    )
    direct_javascript = ImpactDependant(
        kind="import",
        source="web/direct.ts",
        target="web/core.ts",
        path="web/direct.ts",
        line=1,
        confidence=Confidence.HIGH,
        provenance="javascript_static_import",
    )

    selected = _merge_dependants(
        (direct_python,),
        (transitive_python,),
        (direct_javascript,),
    )[:2]

    assert {item.provenance for item in selected} == {
        "python_ast",
        "javascript_static_import",
    }
    assert not any("transitive" in item.provenance for item in selected)
