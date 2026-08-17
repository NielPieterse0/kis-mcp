from __future__ import annotations

from ...capabilities.contracts import (
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
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=92),
    )


def project_management_workflow_descriptors() -> tuple[WorkflowDescriptor, ...]:
    read = OperationEffect.READ_ONLY
    change = OperationEffect.LOCAL_CHANGE
    external = OperationEffect.EXTERNAL
    process = OperationEffect.PROCESS
    return (
        _workflow(
            "capture-project-work",
            "Capture project work",
            "Capture one bounded source issue and reconcile it into the configured Work Management command plane without duplicating Project-owned metadata in the issue body.",
            ("project_management.read", "project_management.write"),
            ("project_management_inventory", "project_management_reconcile"),
            (
                "project identity is explicit",
                "source issue is unique",
                "preview is reviewed",
                "apply uses idempotency",
            ),
            ("capture work", "add project item", "project intake"),
            (read, external, change),
        ),
        _workflow(
            "take-next-project-work",
            "Take the next ready work item",
            "Read the live command plane, select the next deterministic Ready and unclaimed issue, then establish an execution claim before activation.",
            ("project_management.read", "project_management.write", "work.reconcile"),
            ("project_management_take_next_work",),
            (
                "selection uses the configured priority, effort, age, and stable tie-break order",
                "blocked or already claimed work is excluded",
                "the execution claim is established and re-read before Active",
            ),
            ("take next work", "do next work item", "claim next ready work"),
            (read, external, change),
        ),
        _workflow(
            "manage-project-work-state",
            "Manage work command state",
            "Apply bounded command-plane transitions such as Ready, On Hold, Deferred, release, or guarded completion while preserving the configured authority direction.",
            ("project_management.read", "project_management.write", "work.reconcile"),
            (
                "project_management_transition_work",
                "project_management_hold_work",
                "project_management_defer_work",
                "project_management_release_work",
                "project_management_complete_work",
            ),
            (
                "transition is declared by command-plane settings",
                "hold or defer metadata requirements are satisfied",
                "terminal completion remains evidence-gated",
            ),
            (
                "hold work",
                "defer work",
                "release work",
                "complete work",
                "change work status",
            ),
            (read, external, change),
        ),
        _workflow(
            "persist-review-evidence",
            "Persist review evidence",
            "Write one validated review artifact atomically beneath the repository evidence namespace.",
            ("review.evidence.persist",),
            ("project_management_persist_review",),
            ("manifest path is canonical", "write is atomic", "conflicts are retained"),
            ("persist review evidence", "save review report"),
            (change,),
        ),
        _workflow(
            "inspect-project-schema",
            "Inspect and plan Project schema commissioning",
            "Compare the live shared Project against the portfolio-owned schema manifest and return a typed repair plan, including explicit bounded-provider gaps.",
            ("project_management.read", "work.reconcile"),
            ("project_management_schema_status", "project_management_schema_plan"),
            (
                "field and option drift is explicit",
                "view observability is explicit",
                "provider gaps are not reported as successful repair",
                "portfolio schema remains authoritative",
            ),
            (
                "project schema",
                "project fields",
                "project commissioning",
                "schema repair plan",
            ),
            (read, external),
        ),
        _workflow(
            "sync-change-classification",
            "Sync authoritative change classification",
            "Read one schema-v4 local change scope and project its exact Change ID, Complexity, Risk Triggers, and Change Created delivery stage into Work Management.",
            ("project_management.write", "work.reconcile"),
            ("project_management_sync_change_classification",),
            (
                "classification comes from the authoritative local scope",
                "only evidence-direction fields are projected",
                "revision conflicts are not overwritten",
            ),
            (
                "sync change classification",
                "project complexity and risk",
                "change governance projection",
            ),
            (read, external, change),
        ),
        _workflow(
            "reconcile-project-state",
            "Reconcile project state",
            "Compare desired and observed work state, preview deterministic actions, and apply bounded changes explicitly.",
            ("project_management.read", "project_management.write", "work.reconcile"),
            ("project_management_inventory", "project_management_reconcile"),
            (
                "drift is explicit",
                "conflicts are not overwritten",
                "per-record outcomes are returned",
            ),
            ("reconcile project", "project drift", "repair project state"),
            (external, change, read),
        ),
        _workflow(
            "report-programme-status",
            "Report programme status",
            "Aggregate configured projects while preserving blockers, risks, gaps, failures, and truncation.",
            ("programme.status.report",),
            ("project_management_portfolio_status",),
            (
                "project identity is retained",
                "partial data is disclosed",
                "output is bounded",
            ),
            ("programme status", "portfolio status", "project blockers"),
            (read,),
        ),
        _workflow(
            "verify-change-traceability",
            "Verify change traceability",
            "Evaluate one provider-neutral implementation trace at an explicit lifecycle stage.",
            ("work.traceability.verify",),
            ("project_management_verify_traceability",),
            ("stage is explicit", "issues are classified", "no provider layout leaks"),
            ("verify traceability", "change evidence"),
            (read,),
        ),
        _workflow(
            "complete-work-managed-pull-request",
            "Complete a work-managed pull request",
            "Observe the exact pull-request head, execute canonical local verification for that head, require Work Management command state to permit landing, merge only that approved head, then record the post-merge documentation milestone before Done.",
            (
                "github.pull-request.read",
                "operation.execute_change_workflow",
                "work.traceability.verify",
                "operation.kis_github_merge_registered_pull_request",
                "work.reconcile",
            ),
            (
                "github_pull_request_read",
                "execute_change_workflow",
                "project_management_merge_readiness",
                "kis_github_merge_registered_pull_request",
                "project_management_documentation_reconcile",
            ),
            (
                "referenced local verification matches the exact pull-request head",
                "an unready merge gate stops this workflow before merge",
                "only the exact approved head is merged",
                "documentation_reconciliation_due is evidence-linked after merge",
                "post_merge_complete is required before Done",
            ),
            (
                "merge work-managed pull request",
                "documentation closeout",
                "post merge documentation",
            ),
            (read, external, change, process),
        ),
    )


__all__ = ["project_management_workflow_descriptors"]
