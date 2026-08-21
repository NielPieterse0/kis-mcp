from __future__ import annotations

import asyncio
from typing import Any

from kis_mcp.commissioning.models import (
    ChangeClassification,
    ClassificationState,
    CommissioningIntakeOutcome,
    CommissioningObligation,
    IntakeDisposition,
    LandedChangeEvidence,
)
from kis_mcp.commissioning.projection import (
    aggregate_commissioning_key,
    aggregate_live_state,
    project_classification_state,
    project_source_live_state,
)


class FakeInvoker:
    def __init__(self) -> None:
        self.changes: list[tuple[str, dict[str, Any]]] = []

    async def read(self, operation: str, arguments: dict[str, Any]) -> Any:
        assert operation == "project_management_board_data"
        assert arguments["include_history"] is True
        return {
            "provenance": {"complete": True},
            "result": {
                "complete": True,
                "truncated": False,
                "cards": [
                    {
                        "item_id": "PVTITEM",
                        "repository": "NielPieterse0/kis-mcp",
                        "number": 454,
                        "authority_revision": "rev-1",
                    }
                ],
            },
        }

    async def change(self, operation: str, arguments: dict[str, Any]) -> Any:
        self.changes.append((operation, dict(arguments)))
        return {"outcomes": [{"success": True, "applied": True}]}


def test_aggregate_key_is_exact_for_one_and_set_digest_for_many() -> None:
    one = "commission:nielpieterse0/kis-mcp:" + "a" * 40 + ":gateway-runtime"
    two = "commission:nielpieterse0/kis-mcp:" + "a" * 40 + ":work-management"
    assert aggregate_commissioning_key("NielPieterse0/kis-mcp", "a" * 40, (one,)) == one
    result = aggregate_commissioning_key(
        "NielPieterse0/kis-mcp", "a" * 40, (two, one)
    )
    assert result.startswith("commission:nielpieterse0/kis-mcp:" + "a" * 40 + ":set-")
    assert len(result.rsplit("set-", 1)[-1]) == 24


def test_aggregate_live_state_uses_failed_blocked_pending_passed_precedence() -> None:
    assert aggregate_live_state(("passed", "passed")) == "Passed"
    assert aggregate_live_state(("passed", "pending")) == "Pending"
    assert aggregate_live_state(("passed", "blocked")) == "Blocked"
    assert aggregate_live_state(("blocked", "failed", "pending")) == "Failed"


def test_projection_writes_only_live_verification_fields() -> None:
    invoker = FakeInvoker()
    result = asyncio.run(
        project_source_live_state(
            invoker,
            project_id="kis-mcp",
            repository="NielPieterse0/kis-mcp",
            source_issue=454,
            live_state="Passed",
            commissioning_key="commission:key",
            evidence_reference="commissioning-evidence:" + "b" * 64,
            idempotency_key="project-pass",
        )
    )
    assert result["projected"] is True
    operation, arguments = invoker.changes[0]
    assert operation == "project_management_reconcile"
    assert arguments["supported_fields"] == [
        "Live Verification",
        "Commissioning Key",
        "Live Verification Evidence",
    ]
    fields = arguments["desired"][0]["fields"]
    assert fields["Live Verification"] == "Passed"
    assert "Verification" not in fields
    assert set(fields) == set(arguments["supported_fields"])


def _classification_evidence() -> LandedChangeEvidence:
    return LandedChangeEvidence(
        repository="NielPieterse0/kis-mcp",
        source_issue=454,
        source_pr=456,
        merge_sha="a" * 40,
        change_id="229-commissioning-runner-evidence-lifecycle",
        changed_paths=("src/kis_mcp/work_management/service.py",),
        risk_triggers=(),
    )


def _obligation(surface_id: str) -> CommissioningObligation:
    return CommissioningObligation(
        surface_id=surface_id,
        commissioning_key=f"commission:nielpieterse0/kis-mcp:{'a' * 40}:{surface_id}",
        runtime_instance="kis-op",
        refresh_rule="restart",
        probe_id="work-management-contract",
        verification_procedure="procedure",
        expected_invariant="invariant",
        evidence_target="target",
        terminal_success_criterion="criterion",
        matched_paths=("src/kis_mcp/work_management/service.py",),
        matched_risk_triggers=(),
    )

def test_required_classification_projects_pending_with_sorted_issue_linkage() -> None:
    first = _obligation("provider-runtime")
    second = _obligation("work-management")
    classification = ChangeClassification(
        state=ClassificationState.REQUIRED,
        obligations=(first, second),
    )
    intake = (
        CommissioningIntakeOutcome(
            surface_id=second.surface_id,
            commissioning_key=second.commissioning_key,
            disposition=IntakeDisposition.CREATED,
            issue_number=462,
        ),
        CommissioningIntakeOutcome(
            surface_id=first.surface_id,
            commissioning_key=first.commissioning_key,
            disposition=IntakeDisposition.CREATED,
            issue_number=461,
        ),
    )
    invoker = FakeInvoker()
    asyncio.run(
        project_classification_state(
            invoker,
            project_id="kis-mcp",
            evidence=_classification_evidence(),
            classification=classification,
            intake=intake,
        )
    )
    fields = invoker.changes[-1][1]["desired"][0]["fields"]
    assert fields["Live Verification"] == "Pending"
    assert fields["Commissioning Key"].startswith(
        f"commission:nielpieterse0/kis-mcp:{'a' * 40}:set-"
    )
    assert len(fields["Commissioning Key"].rsplit("set-", 1)[-1]) == 24
    assert fields["Live Verification Evidence"] == "commissioning-issues:461,462"
    assert "Verification" not in fields


def test_not_required_classification_clears_key_without_source_verification() -> None:
    invoker = FakeInvoker()
    asyncio.run(
        project_classification_state(
            invoker,
            project_id="kis-mcp",
            evidence=_classification_evidence(),
            classification=ChangeClassification(state=ClassificationState.NOT_REQUIRED),
            intake=(),
        )
    )
    fields = invoker.changes[-1][1]["desired"][0]["fields"]
    assert fields["Live Verification"] == "Not Required"
    assert fields["Commissioning Key"] is None
    assert fields["Live Verification Evidence"].endswith(":not_required")
    assert "Verification" not in fields

def test_ambiguous_classification_projects_blocked_without_invented_key() -> None:
    invoker = FakeInvoker()
    asyncio.run(
        project_classification_state(
            invoker,
            project_id="kis-mcp",
            evidence=_classification_evidence(),
            classification=ChangeClassification(
                state=ClassificationState.BLOCKED_AMBIGUOUS,
                ambiguous_risk_triggers=("security",),
            ),
            intake=(),
        )
    )
    fields = invoker.changes[-1][1]["desired"][0]["fields"]
    assert fields["Live Verification"] == "Blocked"
    assert fields["Commissioning Key"] is None
    assert ":blocked_ambiguous:" in fields["Live Verification Evidence"]
    assert "Verification" not in fields