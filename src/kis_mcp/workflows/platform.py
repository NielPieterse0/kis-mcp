from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import RuntimeConfig
from ..providers.platform import ProviderService, build_platform_nvidia_backend
from ..tools.platform import build_platform_codex_backend
from .code_review import (
    AgentSettings,
    CodeReviewAgent,
    GitReviewEvidenceCollector,
    load_agent_settings_or_disabled,
    UnavailableReviewBackend,
    register_agent_tools,
)

from ..capabilities.contracts import (
    ExposureMode,
    ExposurePolicy,
    OperationEffect,
    WorkflowDescriptor,
)


def _workflow(
    workflow_id: str,
    title: str,
    description: str,
    capabilities: tuple[str, ...],
    steps: tuple[str, ...],
    criteria: tuple[str, ...],
    terms: tuple[str, ...],
    effects: tuple[OperationEffect, ...],
) -> WorkflowDescriptor:
    return WorkflowDescriptor(
        workflow_id=workflow_id,
        title=title,
        description=description,
        capabilities=capabilities,
        required_steps=steps,
        completion_criteria=criteria,
        activation_terms=terms,
        effects=effects,
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=90),
    )


def workflow_descriptors() -> tuple[WorkflowDescriptor, ...]:
    read = OperationEffect.READ_ONLY
    change = OperationEffect.LOCAL_CHANGE
    external = OperationEffect.EXTERNAL
    process = OperationEffect.PROCESS
    return (
        _workflow(
            "assess-repository-modularity",
            "Assess repository modularity",
            "Collect repository evidence, score module boundaries, and propose reversible changes.",
            ("architecture.modularity.assess", "repository.inspect", "repository.git-read"),
            ("inspect_project", "load_skill", "read_file"),
            ("evidence is recorded", "scores identify unknowns", "recommendations are reversible"),
            ("modularity assessment", "module boundary", "decompose architecture"),
            (read,),
        ),
        _workflow(
            "clean-repository-worktrees",
            "Clean merged repository worktrees",
            "Validate merged clean worktrees and remove only eligible change worktrees.",
            ("git.worktree.cleanup", "repository.git-read", "verification.execute"),
            ("list_worktrees", "validate_change_claims", "cleanup_change_worktree"),
            ("worktree is merged", "worktree is clean", "branch removal is non-forced"),
            ("clean worktrees", "prune worktrees", "repository cleanup"),
            (read, change, process),
        ),
        _workflow(
            "commission-provider",
            "Commission an optional provider",
            "Run local preflight, complete supervised authentication, and verify namespaced exposure.",
            ("provider.status.inspect", "provider.authenticate", "provider.live-verify"),
            ("kis_provider_status", "provider_preflight", "provider_authenticate", "provider_smoke"),
            ("provider is mounted", "authentication is verified", "live operation succeeds"),
            ("commission provider", "authenticate provider", "provider setup"),
            (read, external, process),
        ),
        _workflow(
            "create-or-improve-skill",
            "Create or improve a shared skill",
            "Evaluate skill metadata and mutate the approved shared catalogue through Work.",
            ("skill.create", "skill.improve", "skill.evaluate"),
            ("evaluate_skill", "create_skill", "improve_skill"),
            ("metadata is complete", "catalogue refresh succeeds", "change is recoverable"),
            ("create skill", "improve skill", "skill catalogue"),
            (read, change),
        ),
        _workflow(
            "develop-isolated-change",
            "Develop an isolated repository change",
            "Create a claimed worktree, implement with tests, verify, and prepare reviewable commits.",
            ("code.change.plan", "code.change.implement", "git.worktree.create", "verification.execute"),
            ("inspect_project", "create_change_worktree", "run_tests", "commit_change"),
            ("scope check passes", "required verification passes", "commits are reviewable"),
            ("develop isolated change", "new worktree", "implementation slice"),
            (read, change, process),
        ),
        _workflow(
            "diagnose-provider-startup",
            "Diagnose provider startup",
            "Inspect readiness, configuration, mount state, and corrective startup actions.",
            ("provider.status.inspect", "provider.startup.diagnose", "repository.inspect"),
            ("kis_provider_status", "kis_health", "read_provider_logs"),
            ("failure layer is identified", "corrective action is explicit", "secrets remain redacted"),
            ("provider startup", "provider unavailable", "provider mount failed"),
            (read,),
        ),
        _workflow(
            "pull-request-safe-closeout",
            "Review and merge pull request safely",
            "Inspect, verify, review, merge the exact approved head, and clean the merged worktree.",
            ("git.change.inspect", "validation.execute", "github.review", "github.pull-request.merge", "git.worktree.cleanup"),
            ("inspect_change", "run_verification", "github_review_pull_request", "github_merge_pull_request", "cleanup_change_worktree"),
            ("checks pass", "review findings are resolved", "approved head is merged", "worktree is cleaned"),
            ("review and merge pull request", "merge pr safely", "pr completion", "clean worktree"),
            (read, change, external, process),
        ),
        _workflow(
            "review-current-change",
            "Review the current change",
            "Inspect the working tree, collect bounded evidence, and return findings-first review output.",
            ("git.change.inspect", "code.change.review", "regression.detect"),
            ("inspect_change", "review_change_with_agent"),
            ("changed behavior is traced", "findings are evidence-linked", "verification gaps are stated"),
            ("review current change", "review diff", "code review"),
            (read,),
        ),
    )


def _build_code_review_agent(
    runtime: RuntimeConfig,
    settings: AgentSettings,
    provider_service: ProviderService,
) -> CodeReviewAgent:
    nvidia_backend: Any = UnavailableReviewBackend("nvidia-nim")
    try:
        nvidia_backend = build_platform_nvidia_backend(provider_service, settings.nvidia)
    except Exception:
        nvidia_backend = UnavailableReviewBackend("nvidia-nim")
    codex_backend: Any = UnavailableReviewBackend("codex-cli")
    try:
        codex_backend = build_platform_codex_backend(settings.codex)
    except Exception:
        codex_backend = UnavailableReviewBackend("codex-cli")
    return CodeReviewAgent(
        settings,
        collector=GitReviewEvidenceCollector(
            project_boundary=Path(runtime.project_boundary),
            max_chars=settings.max_evidence_chars,
        ),
        backends={"nvidia-nim": nvidia_backend, "codex-cli": codex_backend},
    )


def load_platform_workflow_settings():
    return load_agent_settings_or_disabled()


def register_platform_workflows(
    server,
    runtime: RuntimeConfig,
    settings: AgentSettings,
    provider_service: ProviderService,
) -> None:
    register_agent_tools(
        server,
        _build_code_review_agent(runtime, settings, provider_service),
    )


__all__ = [
    "AgentSettings",
    "load_platform_workflow_settings",
    "register_platform_workflows",
    "workflow_descriptors",
]
