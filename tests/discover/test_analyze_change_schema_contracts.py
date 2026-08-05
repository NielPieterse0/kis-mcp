from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from kis_mcp.discover.change_analysis import (
    AnalyzeChangeRequest,
    AnalyzeChangeService,
    GitHubChangeContext,
    SuppliedChange,
)
from kis_mcp.discover.impact_contracts import ImpactBudget

from .test_analyze_change_workflow import _ChangeService, _ImpactService


ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> dict:
    return json.loads((ROOT / "contracts" / "discover" / name).read_text(encoding="utf-8"))


def test_analyze_change_request_matches_checked_in_schema() -> None:
    request = AnalyzeChangeRequest(
        project=r"C:\Projects\fixture",
        source="supplied",
        task_terms=("contract",),
        supplied_changes=(SuppliedChange(path="settings/app.json"),),
        github_context=GitHubChangeContext(
            repository="owner/repo",
            pull_number=9,
            base_sha="a" * 40,
            head_sha="b" * 40,
            changes=(SuppliedChange(path="contracts/api.schema.json", status="added"),),
        ),
        budget=ImpactBudget(10, 10, 10, 10),
    )

    assert list(Draft202012Validator(_schema("analyze-change-request.schema.json")).iter_errors(request.to_json_dict())) == []


def test_analyze_change_response_matches_checked_in_schema() -> None:
    response = AnalyzeChangeService(
        change_service=_ChangeService(("src/app.py",)),
        impact_service=_ImpactService(),
    ).analyze(
        AnalyzeChangeRequest(
            project=r"C:\Projects\fixture",
            source="working_tree",
            task_terms=("app",),
            budget=ImpactBudget(10, 10, 10, 10),
        )
    )

    assert list(Draft202012Validator(_schema("analyze-change-response.schema.json")).iter_errors(response.to_json_dict())) == []
