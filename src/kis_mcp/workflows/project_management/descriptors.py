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
    return (
        _workflow(
            "capture-project-work",
            "Capture project work",
            "Inspect one configured Project and reconcile one bounded work item.",
            ("project_management.read", "project_management.write"),
            ("project_management_inventory", "project_management_reconcile"),
            ("project identity is explicit", "preview is reviewed", "apply uses idempotency"),
            ("capture work", "add project item", "project intake"),
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
            "Inspect project schema",
            "Compare the configured GitHub Project field surface against the repository-owned schema manifest and report unobservable views explicitly.",
            ("project_management.read", "work.reconcile"),
            ("project_management_schema_status",),
            ("field drift is explicit", "view observability is explicit", "repository schema remains authoritative"),
            ("project schema", "project fields", "project commissioning"),
            (read, external),
        ),
        _workflow(
            "reconcile-project-state",
            "Reconcile project state",
            "Compare desired and observed work state, preview deterministic actions, and apply bounded changes explicitly.",
            ("project_management.read", "project_management.write", "work.reconcile"),
            ("project_management_inventory", "project_management_reconcile"),
            ("drift is explicit", "conflicts are not overwritten", "per-record outcomes are returned"),
            ("reconcile project", "project drift", "repair project state"),
            (external, change, read),
        ),
        _workflow(
            "report-programme-status",
            "Report programme status",
            "Aggregate configured projects while preserving blockers, risks, gaps, failures, and truncation.",
            ("programme.status.report",),
            ("project_management_portfolio_status",),
            ("project identity is retained", "partial data is disclosed", "output is bounded"),
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
            "Require a ready Work Management gate, merge only the exact approved pull-request head, then record the post-merge documentation milestone before Done.",
            (
                "work.traceability.verify",
                "operation.kis_github_merge_registered_pull_request",
                "work.reconcile",
            ),
            (
                "project_management_merge_readiness",
                "kis_github_merge_registered_pull_request",
                "project_management_documentation_reconcile",
            ),
            (
                "an unready merge gate stops this workflow before merge",
                "only the exact approved head is merged",
                "documentation_reconciliation_due is evidence-linked after merge",
                "post_merge_complete is required before Done",
            ),
            ("merge work-managed pull request", "documentation closeout", "post merge documentation"),
            (read, external, change),
        ),
    )


__all__ = ["project_management_workflow_descriptors"]
