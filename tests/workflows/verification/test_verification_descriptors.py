from __future__ import annotations

from kis_mcp.workflows.verification.descriptors import (
    CI_FAILURE_CLASSES,
    verification_workflow_descriptors,
)


def test_verification_workflows_are_discoverable_and_explicit_about_execution() -> None:
    workflows = {item.workflow_id: item for item in verification_workflow_descriptors()}

    verify = workflows["verify-current-change"]
    assert verify.required_steps == (
        "inspect_change",
        "analyze_change",
        "run_verification",
    )
    assert verify.executable_steps == verify.required_steps
    assert "verification.execute" in verify.capabilities
    assert "verify current change" in verify.activation_terms

    triage = workflows["triage-exact-head-ci"]
    assert triage.required_steps == (
        "inspect_change",
        "github_actions_list",
        "github_actions_get",
    )
    assert triage.executable_steps == triage.required_steps
    assert "github.actions.read" in triage.capabilities
    assert "exact-head ci" in triage.activation_terms


def test_exact_head_ci_failure_classes_are_stable_and_complete() -> None:
    assert CI_FAILURE_CLASSES == (
        "implementation_defect",
        "test_defect",
        "governance_topology",
        "stale_base",
        "provider_tooling_defect",
        "runner_environment",
        "timeout_incomplete",
        "unresolved",
    )
