from __future__ import annotations

import asyncio
from typing import Any

import kis_mcp.commissioning_runtime.processor as processor_module
from kis_mcp.commissioning.models import (
    ChangeClassification,
    ClassificationState,
    CommissioningIntakeOutcome,
    CommissioningObligation,
    IntakeDisposition,
    LandedChangeEvidence,
)
from kis_mcp.commissioning.settings import load_post_merge_commissioning_settings
from kis_mcp.commissioning_runtime.processor import CommissioningCandidateProcessor

REPOSITORY = "NielPieterse0/kis-mcp"
MERGE = "a" * 40
KEY = f"commission:nielpieterse0/kis-mcp:{MERGE}:work-management"


def _evidence() -> LandedChangeEvidence:
    return LandedChangeEvidence(
        repository=REPOSITORY,
        source_issue=454,
        source_pr=456,
        merge_sha=MERGE,
        change_id="229-commissioning-runner-evidence-lifecycle",
        changed_paths=("src/kis_mcp/work_management/service.py",),
        risk_triggers=(),
    )

def _classification() -> ChangeClassification:
    return ChangeClassification(
        state=ClassificationState.REQUIRED,
        obligations=(
            CommissioningObligation(
                surface_id="work-management",
                commissioning_key=KEY,
                runtime_instance="kis-op",
                refresh_rule="restart",
                probe_id="work-management-contract",
                verification_procedure="procedure",
                expected_invariant="invariant",
                evidence_target="target",
                terminal_success_criterion="criterion",
                matched_paths=("src/kis_mcp/work_management/service.py",),
                matched_risk_triggers=(),
            ),
        ),
    )


class FakeResolver:
    def __init__(self, _invoker: Any, _settings: Any) -> None:
        pass

    async def resolve(self, repository: str, pull_number: int) -> LandedChangeEvidence:
        assert repository == REPOSITORY
        assert pull_number == 456
        return _evidence()

class FakeIntake:
    def __init__(self, _invoker: Any) -> None:
        pass

    async def intake(
        self,
        _evidence_value: LandedChangeEvidence,
        _classification_value: ChangeClassification,
    ) -> tuple[CommissioningIntakeOutcome, ...]:
        return (
            CommissioningIntakeOutcome(
                surface_id="work-management",
                commissioning_key=KEY,
                disposition=IntakeDisposition.CREATED,
                issue_number=460,
            ),
        )


class FakeInvoker:
    def __init__(self) -> None:
        self.change_calls: list[tuple[str, dict[str, Any]]] = []

    async def read(self, operation: str, arguments: dict[str, Any]) -> Any:
        assert operation == "project_management_board_data"
        assert arguments["query"] == "454"
        return {
            "provenance": {"complete": True},
            "result": {"complete": True, "truncated": False, "cards": [
                {"item_id": "ITEM-454", "repository": REPOSITORY, "number": 454,
                 "authority_revision": "rev-454"}
            ]},
        }
    async def change(self, operation: str, arguments: dict[str, Any]) -> Any:
        self.change_calls.append((operation, dict(arguments)))
        return {"outcomes": [{"success": True, "applied": True}]}



def test_candidate_processor_projects_pending_after_intake(monkeypatch: Any) -> None:
    monkeypatch.setattr(processor_module, "MergedChangeResolver", FakeResolver)
    monkeypatch.setattr(processor_module, "CommissioningIntakeService", FakeIntake)
    monkeypatch.setattr(processor_module, "classify_change", lambda _e, _s: _classification())
    invoker = FakeInvoker()

    result = asyncio.run(
        CommissioningCandidateProcessor(load_post_merge_commissioning_settings())(
            REPOSITORY,
            456,
            invoker,
        )
    )

    assert result["classification"] == "required"
    assert result["commissioning_keys"] == [KEY]
    assert result["issue_numbers"] == [460]
    projection = invoker.change_calls[-1][1]
    fields = projection["desired"][0]["fields"]
    assert fields["Live Verification"] == "Pending"
    assert fields["Commissioning Key"] == KEY
    assert fields["Live Verification Evidence"] == "commissioning-issues:460"
    assert "Verification" not in fields