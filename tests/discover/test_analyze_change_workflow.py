from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from kis_mcp.discover.change_analysis import (
    AnalyzeChangeRequest,
    AnalyzeChangeService,
    GitHubChangeContext,
    SuppliedChange,
)
from kis_mcp.discover.contracts import Confidence, ProjectIdentity
from kis_mcp.discover.impact_contracts import (
    ImpactBudget,
    ImpactOmissions,
    InspectImpactResponse,
)


class _ChangeResponse:
    def __init__(self, paths: tuple[str, ...]) -> None:
        self.changed_files = tuple(type("Changed", (), {"path": path})() for path in paths)

    def to_json_dict(self) -> dict[str, Any]:
        return {"tool": "inspect_change", "changed_files": [{"path": item.path} for item in self.changed_files]}


class _ChangeService:
    def __init__(self, paths: tuple[str, ...]) -> None:
        self.paths = paths
        self.requests: list[Any] = []

    def inspect(self, request: Any) -> _ChangeResponse:
        self.requests.append(request)
        return _ChangeResponse(self.paths)


class _ImpactService:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    def inspect(self, request: Any) -> InspectImpactResponse:
        self.requests.append(request)
        return InspectImpactResponse(
            project=ProjectIdentity(
                project_id="local:test",
                canonical_path=request.project,
                repository_root=request.project,
                git_root=request.project,
                remote_identity=None,
            ),
            changed_paths=request.changed_paths,
            changed_symbols=(),
            dependants=(),
            relationship_impacts=(),
            task_term_matches=tuple(request.task_terms),
            affected_tests=(),
            verification_handoffs=(),
            implementation_steps=(),
            unknowns=(),
            omissions=ImpactOmissions(0, 0, 0, 0),
            confidence=Confidence.HIGH,
            truncated=False,
            truncation_reasons=(),
            fingerprint="0" * 64,
        )


def _budget() -> ImpactBudget:
    return ImpactBudget(20, 20, 20, 20)


def test_request_normalizes_task_terms_supplied_changes_and_github_context() -> None:
    request = AnalyzeChangeRequest(
        project=r"C:\Projects\fixture",
        source="supplied",
        task_terms=(" Auth ", "auth", "token"),
        supplied_changes=(
            SuppliedChange(path="./src/auth.py", status="modified"),
            SuppliedChange(path="src/auth.py", status="modified"),
        ),
        github_context=GitHubChangeContext(
            repository=" owner/repo ",
            pull_number=42,
            base_sha="A" * 40,
            head_sha="B" * 40,
            changes=(SuppliedChange(path="contracts/api.schema.json", status="modified"),),
        ),
        budget=_budget(),
    )

    assert request.task_terms == ("auth", "token")
    assert tuple(item.path for item in request.supplied_changes) == ("src/auth.py",)
    assert request.github_context is not None
    assert request.github_context.repository == "owner/repo"
    assert request.github_context.base_sha == "a" * 40
    assert request.github_context.head_sha == "b" * 40


def test_service_uses_local_change_inventory_and_passes_task_terms_to_impact() -> None:
    change = _ChangeService(("src/auth.py", "tests/test_auth.py"))
    impact = _ImpactService()
    service = AnalyzeChangeService(change_service=change, impact_service=impact)

    response = service.analyze(
        AnalyzeChangeRequest(
            project=r"C:\Projects\fixture",
            source="working_tree",
            task_terms=("authentication",),
            budget=_budget(),
        )
    )

    assert response.normalized_change.source == "working_tree"
    assert response.normalized_change.changed_paths == ("src/auth.py", "tests/test_auth.py")
    assert impact.requests[0].task_terms == ("authentication",)
    assert response.to_json_dict()["tool"] == "analyze_change"


def test_service_normalizes_supplied_and_github_changes_without_connector_execution() -> None:
    change = _ChangeService(("ignored.py",))
    impact = _ImpactService()
    service = AnalyzeChangeService(change_service=change, impact_service=impact)

    response = service.analyze(
        AnalyzeChangeRequest(
            project=r"C:\Projects\fixture",
            source="supplied",
            task_terms=("contract",),
            supplied_changes=(SuppliedChange(path="settings/app.json", status="modified"),),
            github_context=GitHubChangeContext(
                repository="owner/repo",
                pull_number=7,
                base_sha="a" * 40,
                head_sha="b" * 40,
                changes=(SuppliedChange(path="contracts/api.schema.json", status="added"),),
            ),
            budget=_budget(),
        )
    )

    assert change.requests == []
    assert response.normalized_change.changed_paths == (
        "contracts/api.schema.json",
        "settings/app.json",
    )
    assert response.normalized_change.github_context is not None
    assert response.normalized_change.github_context.pull_number == 7
    assert impact.requests[0].changed_paths == response.normalized_change.changed_paths


def test_service_rejects_supplied_change_input_beyond_configured_limit() -> None:
    service = AnalyzeChangeService(
        change_service=_ChangeService(()),
        impact_service=_ImpactService(),
        max_changes=1,
        max_task_terms=4,
    )
    request = AnalyzeChangeRequest(
        project=r"C:\Projects\fixture",
        source="supplied",
        supplied_changes=(
            SuppliedChange(path="src/a.py"),
            SuppliedChange(path="src/b.py"),
        ),
        budget=_budget(),
    )

    with pytest.raises(ValueError, match="supplied change limit"):
        service.analyze(request)


def test_service_rejects_task_terms_beyond_configured_limit() -> None:
    service = AnalyzeChangeService(
        change_service=_ChangeService(("src/a.py",)),
        impact_service=_ImpactService(),
        max_changes=4,
        max_task_terms=1,
    )
    request = AnalyzeChangeRequest(
        project=r"C:\Projects\fixture",
        source="working_tree",
        task_terms=("one", "two"),
        budget=_budget(),
    )

    with pytest.raises(ValueError, match="task term limit"):
        service.analyze(request)
