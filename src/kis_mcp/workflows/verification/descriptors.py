from __future__ import annotations

from dataclasses import dataclass

from ...capabilities.contracts import OperationEffect

CI_FAILURE_CLASSES = (
    "implementation_defect",
    "test_defect",
    "governance_topology",
    "stale_base",
    "provider_tooling_defect",
    "runner_environment",
    "timeout_incomplete",
    "unresolved",
)


@dataclass(frozen=True, slots=True)
class VerificationWorkflowSpec:
    workflow_id: str
    title: str
    description: str
    capabilities: tuple[str, ...]
    required_steps: tuple[str, ...]
    executable_steps: tuple[str, ...]
    completion_criteria: tuple[str, ...]
    activation_terms: tuple[str, ...]
    effects: tuple[OperationEffect, ...]

    def __post_init__(self) -> None:
        required = set(self.required_steps)
        if not self.executable_steps:
            raise ValueError("verification workflow executable_steps must not be empty")
        if any(step not in required for step in self.executable_steps):
            raise ValueError("verification workflow executable_steps must be required_steps")


def verification_workflow_descriptors() -> tuple[VerificationWorkflowSpec, ...]:
    read = OperationEffect.READ_ONLY
    process = OperationEffect.PROCESS
    external = OperationEffect.EXTERNAL
    verify = VerificationWorkflowSpec(
        workflow_id="verify-current-change",
        title="Verify current change",
        description=(
            "Inspect and analyze the current repository change, execute affected "
            "verification IDs through Work, and return bounded evidence."
        ),
        capabilities=(
            "git.change.inspect",
            "change.impact.analyze",
            "verification.execute",
        ),
        required_steps=("inspect_change", "analyze_change", "run_verification"),
        executable_steps=("inspect_change", "analyze_change", "run_verification"),
        completion_criteria=(
            "affected verification IDs are resolved",
            "selected verification evidence is complete",
            "failures are classified without suppressing policy errors",
        ),
        activation_terms=(
            "verify current change",
            "run affected verification",
            "validate this change",
            "focused verification",
            "change verification",
        ),
        effects=(read, process),
    )
    triage = VerificationWorkflowSpec(
        workflow_id="triage-exact-head-ci",
        title="Triage exact-head CI failure",
        description=(
            "Inspect the expected change and exact-head GitHub Actions evidence, "
            "then classify whether the failure belongs to implementation, tests, "
            "governance topology, base state, provider tooling, or runner environment."
        ),
        capabilities=("git.change.inspect", "github.actions.read"),
        required_steps=("inspect_change", "github_actions_list", "github_actions_get"),
        executable_steps=("inspect_change", "github_actions_list", "github_actions_get"),
        completion_criteria=(
            "workflow run head matches the expected revision",
            "failing job and step evidence is bounded",
            "failure classification uses the exact-head CI contract",
            "recommended next action is evidence-linked",
        ),
        activation_terms=(
            "exact-head ci",
            "triage ci failure",
            "why did ci fail",
            "github actions failure",
            "classify ci failure",
        ),
        effects=(read, external),
    )
    return (verify, triage)


__all__ = [
    "CI_FAILURE_CLASSES",
    "VerificationWorkflowSpec",
    "verification_workflow_descriptors",
]
