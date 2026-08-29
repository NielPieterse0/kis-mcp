from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from ..capabilities.contracts import (
    ExposureMode,
    ExposurePolicy,
    OperationEffect,
    WorkflowDescriptor,
)
from ..config import RuntimeConfig
from ..discover.change_service import InspectChangeService
from ..discover.git_change_reader import GitChangeReader
from ..discover.read_authority import ReadAuthority
from ..providers.platform import (
    ProviderService,
    build_platform_github_project_backend,
    build_platform_nvidia_backend,
)
from ..tools.platform import build_platform_codex_backend
from ..work_management import (
    ProjectBinding,
    WorkManagementService,
    WorkManagementSettings,
    load_work_management_settings,
)
from .agent_validation import register_platform_agent_validation
from .code_review import (
    AgentSettings,
    CodeReviewAgent,
    GitReviewEvidenceCollector,
    UnavailableReviewBackend,
    load_agent_settings_or_disabled,
    register_agent_tools,
)
from .project_management import (
    project_management_workflow_descriptors,
    register_project_management_tools,
)
from .once_through.tools import register_once_through_tools
from .state_management import register_state_management_tools
from .verification.descriptors import verification_workflow_descriptors


def _workflow(
    workflow_id: str,
    title: str,
    description: str,
    capabilities: tuple[str, ...],
    steps: tuple[str, ...],
    criteria: tuple[str, ...],
    terms: tuple[str, ...],
    effects: tuple[OperationEffect, ...],
    *,
    executable_steps: tuple[str, ...] = (),
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
        executable_steps=executable_steps,
    )


_REGISTERED_MERGE_STEP = "kis_github_merge_registered_pull_request"
_REGISTERED_REFRESH_STEP = "kis_github_refresh_registered_default_branch"
_REGISTERED_REFRESH_CAPABILITY = "operation.kis_github_refresh_registered_default_branch"


def _ensure_post_merge_tracking_refresh(workflow: WorkflowDescriptor) -> WorkflowDescriptor:
    if _REGISTERED_MERGE_STEP not in workflow.required_steps:
        return workflow
    if _REGISTERED_REFRESH_STEP in workflow.required_steps:
        return workflow
    merge_index = workflow.required_steps.index(_REGISTERED_MERGE_STEP)
    steps = (*workflow.required_steps[: merge_index + 1], _REGISTERED_REFRESH_STEP, *workflow.required_steps[merge_index + 1 :])
    capabilities = workflow.capabilities if _REGISTERED_REFRESH_CAPABILITY in workflow.capabilities else (*workflow.capabilities, _REGISTERED_REFRESH_CAPABILITY)
    criteria = (*workflow.completion_criteria, "registered default-branch tracking equals exact GitHub truth")
    return replace(workflow, capabilities=capabilities, required_steps=steps, completion_criteria=criteria)


def workflow_descriptors() -> tuple[WorkflowDescriptor, ...]:
    read = OperationEffect.READ_ONLY
    change = OperationEffect.LOCAL_CHANGE
    external = OperationEffect.EXTERNAL
    process = OperationEffect.PROCESS
    core = (
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
            "inspect-state-ownership",
            "Inspect KIS state ownership",
            "Inventory bounded canonical KIS state namespaces and explain ownership, identity, age, and stale-state safety without reading payload contents.",
            ("state.ownership.inspect",),
            ("state_ownership_inventory",),
            ("ownership class and identities are explicit", "staleness is conservative", "secrets and payload contents are not read"),
            ("state ownership", "stale state", "state diagnostics"),
            (read,),
        ),
        _workflow(
            "cleanup-stale-state",
            "Quarantine stale reconstructible KIS state",
            "Preview one proven-stale reconstructible namespace, then move it through recoverable quarantine only when explicitly applied.",
            ("state.ownership.inspect", "state.stale.quarantine"),
            ("state_ownership_inventory", "state_stale_cleanup"),
            ("preview precedes mutation", "only proven-stale reconstructible state is eligible", "cleanup is quarantine-only and replay-safe"),
            ("cleanup stale state", "quarantine stale cache", "retire stale state"),
            (read, change),
        ),
        _workflow(
            "validate-agent-configuration",
            "Validate agent configuration",
            "Run pinned agnix against one local project with bounded read-only validation settings.",
            ("operation.validate_agent_configuration",),
            ("validate_agent_configuration",),
            ("validation completes", "findings are bounded", "no fix authority is exposed"),
            ("validate agent configuration", "agnix", "lint agent config"),
            (process,),
            executable_steps=("validate_agent_configuration",),
        ),
        _workflow(
            "execute-current-change",
            "Execute current change verification",
            "Execute the existing bounded change workflow to select and run verification and aggregate specialist review results.",
            ("operation.execute_change_workflow",),
            ("execute_change_workflow",),
            (
                "selected verification is executed",
                "specialist review outcomes are retained",
                "no new execution authority is introduced",
            ),
            ("execute change workflow", "verify and review current change", "run change checks"),
            (process,),
            executable_steps=("execute_change_workflow",),
        ),
        _workflow(
            "develop-isolated-change",
            "Develop an isolated repository change",
            "Refresh registered GitHub default-branch tracking before creating a claimed worktree, then implement with tests, verify, and prepare reviewable commits.",
            ("code.change.plan", "code.change.implement", "operation.kis_github_refresh_registered_default_branch", "git.worktree.create", "verification.execute"),
            ("inspect_project", "kis_github_refresh_registered_default_branch", "create_change_worktree", "run_tests", "commit_change"),
            ("registered default-branch tracking equals exact GitHub truth", "scope check passes", "required verification passes", "commits are reviewable"),
            ("develop isolated change", "new worktree", "implementation slice"),
            (read, change, external, process),
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
            "publish-registered-commit",
            "Publish a registered commit exactly",
            "Publish one immutable local commit to its centrally registered GitHub repository and verify the exact remote ref.",
            ("operation.kis_github_publish_registered_commit",),
            ("kis_github_publish_registered_commit",),
            ("expected remote base matches", "exact local commit SHA is published", "remote ref is verified"),
            ("publish existing local commit", "push registered commit", "publish registered repository commit"),
            (external,),
        ),
        _workflow(
            "prepare-reviewable-pull-request",
            "Prepare a verified change for pull-request review",
            "Consume valid PromotionReady implementation evidence when available; otherwise execute only missing or invalid implementation evidence, then reconcile the exact tree onto the remote default parent and create the exact pull request.",
            (
                "operation.execute_change_workflow",
                "operation.kis_github_reconcile_registered_commit",
                "operation.kis_github_create_registered_pull_request",
            ),
            ("prepare_reviewable_pull_request",),
            (
                "change execution passes for the exact commit",
                "the exact verified source tree is reconciled onto the verified remote-default parent",
                "an open non-draft pull request is verified at the exact reconciled head",
            ),
            ("prepare reviewable pull request", "verified change to pr", "complete change for review"),
            (process, external),
            executable_steps=("prepare_reviewable_pull_request",),
        ),
        _workflow(
            "speculative-landing-queue",
            "Integrate registered pull requests through the KIS speculative landing queue",
            "Freeze exact pull-request heads, build cumulative queue candidates, require exact candidate Actions success, advance the registered base only from the generation's exact base, then refresh local tracking from GitHub truth.",
            (
                "github.pull-request.read",
                "github.actions.read",
                "operation.kis_github_merge_queue_status",
                "operation.kis_github_merge_queue_enqueue",
                "operation.kis_github_merge_queue_reconcile",
                "operation.kis_github_merge_queue_land",
                "operation.kis_github_refresh_registered_default_branch",
            ),
            (
                "github_pull_request_read",
                "kis_github_merge_queue_enqueue",
                "kis_github_merge_queue_reconcile",
                "kis_github_merge_queue_land",
                "kis_github_refresh_registered_default_branch",
            ),
            (
                "queue entries freeze exact pull-request heads",
                "candidate evidence matches the exact cumulative candidate SHA",
                "ALLGREEN ordering is preserved",
                "base advancement starts from the exact queue generation base",
                "registered default-branch tracking equals exact GitHub truth",
            ),
            (
                "merge queue",
                "speculative landing",
                "queue pull request",
                "integrate concurrent pull requests",
            ),
            (read, change, external),
        ),
        _workflow(
            "pull-request-safe-closeout",
            "Promote and merge pull request safely",
            "Consume previously established implementation review-closure evidence, observe provider-native GitHub pull-request and Actions evidence for the exact head, merge only that policy-approved head, refresh the verified default-branch tracking ref, retain the remote review branch, and clean the merged worktree. Repository-required human approval remains a provider policy gate and is not a KIS implementation review.",
            ("git.change.inspect", "github.pull-request.read", "github.actions.read", "operation.kis_github_merge_registered_pull_request", "operation.kis_github_refresh_registered_default_branch", "git.worktree.cleanup"),
            ("inspect_change", "github_pull_request_read", "github_actions_list", "github_actions_get", "kis_github_merge_registered_pull_request", "kis_github_refresh_registered_default_branch", "cleanup_change_worktree"),
            ("implementation review-closure evidence is already satisfied", "checks pass", "repository and provider merge policy is satisfied", "approved head is merged", "registered default-branch tracking equals exact GitHub truth", "remote review branch is retained", "worktree is cleaned"),
            ("promote and merge pull request", "merge pr safely", "pr completion", "clean worktree"),
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
    verification = tuple(
        _workflow(
            item.workflow_id,
            item.title,
            item.description,
            item.capabilities,
            item.required_steps,
            item.completion_criteria,
            item.activation_terms,
            item.effects,
            executable_steps=item.executable_steps,
        )
        for item in verification_workflow_descriptors()
    )
    combined = (*core, *project_management_workflow_descriptors(), *verification)
    return tuple(_ensure_post_merge_tracking_refresh(item) for item in combined)


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
            inspector=InspectChangeService(
                GitChangeReader(
                    authority=ReadAuthority(
                        Path(runtime.project_boundary),
                        runtime.discover_settings,
                    ),
                    settings=runtime.discover_settings,
                )
            ),
        ),
        backends={"nvidia-nim": nvidia_backend, "codex-cli": codex_backend},
    )


def _build_work_management_service(
    server: Any,
    provider_service: ProviderService,
    settings: WorkManagementSettings,
) -> WorkManagementService:
    bindings: dict[str, ProjectBinding] = {}
    for project in settings.managed_projects:
        backend = settings.binding(project.backend_binding)
        if backend.provider != "github-mcp" or backend.project_number is None:
            continue
        bindings[project.project_id] = ProjectBinding(
            binding_id=backend.binding_id,
            managed_project_id=project.project_id,
            provider_id="github-mcp",
            owner=backend.owner,
            owner_type=backend.owner_type,
            project_number=backend.project_number,
            repository=project.repository,
        )
    backends: dict[str, Any] = {}
    if bindings:
        try:
            backends["github-mcp"] = build_platform_github_project_backend(
                server,
                provider_service,
                bindings,
            )
        except RuntimeError:
            pass
    return WorkManagementService(settings, backends)


def load_platform_workflow_settings():
    return load_agent_settings_or_disabled()


def register_platform_workflows(
    server,
    runtime: RuntimeConfig,
    settings: AgentSettings,
    provider_service: ProviderService,
    *,
    work_management_settings: WorkManagementSettings | None = None,
    work_management_service: WorkManagementService | None = None,
) -> None:
    register_platform_agent_validation(server, runtime)
    register_agent_tools(
        server,
        _build_code_review_agent(runtime, settings, provider_service),
    )
    register_state_management_tools(server, runtime)
    project_settings = work_management_settings or load_work_management_settings()
    if not project_settings.enabled:
        register_once_through_tools(server, Path(runtime.state_root))
        return
    service = work_management_service or _build_work_management_service(
        server,
        provider_service,
        project_settings,
    )
    register_project_management_tools(server, service)
    register_once_through_tools(
        server,
        Path(runtime.state_root),
        work_management_service=service,
    )


__all__ = [
    "AgentSettings",
    "load_platform_workflow_settings",
    "register_platform_workflows",
    "workflow_descriptors",
]
