from __future__ import annotations

from kis_mcp.capabilities.contracts import OperationEffect
from kis_mcp.workflows.verification.descriptors import VerificationWorkflowSpec
from kis_mcp.workflows.verification.integrity import unresolved_executable_steps
from kis_mcp.workflows.verification.recommendation import workflow_match_score


def _workflow(**overrides):
    values = {
        "workflow_id": "verify-current-change",
        "title": "Verify current change",
        "description": "Analyze the current repository change and execute affected verification evidence.",
        "capabilities": ("change.impact.analyze", "verification.execute"),
        "required_steps": ("inspect_change", "run_verification"),
        "executable_steps": ("inspect_change", "run_verification"),
        "completion_criteria": ("verification evidence is complete",),
        "activation_terms": ("verify current change", "run affected verification"),
        "effects": (OperationEffect.READ_ONLY, OperationEffect.PROCESS),
    }
    values.update(overrides)
    return VerificationWorkflowSpec(**values)


def test_unresolved_executable_steps_only_reports_declared_execution_targets() -> None:
    workflow = _workflow(
        required_steps=("inspect_change", "implement_change", "run_verification"),
        executable_steps=("inspect_change", "run_verification"),
    )

    assert unresolved_executable_steps(
        workflow,
        operation_names={"inspect_change"},
        workflow_ids={"verify-current-change"},
    ) == ("run_verification",)


def test_nested_workflow_ids_are_resolvable_execution_targets() -> None:
    workflow = _workflow(
        required_steps=("verify-current-change",),
        executable_steps=("verify-current-change",),
    )
    assert unresolved_executable_steps(
        workflow,
        operation_names=set(),
        workflow_ids={"verify-current-change"},
    ) == ()


def test_workflow_match_score_weights_id_title_terms_description_and_capabilities() -> None:
    workflow = _workflow()
    strong = workflow_match_score(workflow, "please verify the current change and run verification")
    weak = workflow_match_score(workflow, "inspect repository documentation")

    assert strong.score > weak.score
    assert strong.score >= 70
    assert "workflow id/title match" in strong.reasons
    assert "activation term match" in strong.reasons
    assert "capability match" in strong.reasons
