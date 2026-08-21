from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import Any

from ..acquisition.contracts import REGISTERED_ACQUISITION_OPERATION_SCHEMA
from ..projects.github_exact import REGISTERED_GITHUB_OPERATION_SCHEMAS
from ..projects.github_merge_queue import REGISTERED_GITHUB_MERGE_QUEUE_OPERATION_SCHEMAS
from ..projects.github_tracking import REGISTERED_GITHUB_TRACKING_OPERATION_SCHEMAS
from .contracts import (
    CapabilityContribution,
    CapabilityDomain,
    ExposureMode,
    ExposurePolicy,
    OperationDescriptor,
    OperationEffect,
    ReadinessSnapshot,
    ReadinessState,
)
from .normalization import default_quality

_TOKEN = re.compile(r"[a-z0-9]+")


def _annotation(tool: Any, name: str) -> bool:
    annotations = getattr(tool, "annotations", None)
    if isinstance(annotations, dict):
        return bool(annotations.get(name, False))
    return bool(getattr(annotations, name, False))


def _input_schema(tool: Any) -> Mapping[str, Any]:
    raw = getattr(tool, "input_schema", None)
    if not isinstance(raw, Mapping):
        raw = getattr(tool, "inputSchema", None)
    if not isinstance(raw, Mapping):
        raw = getattr(tool, "parameters", None)
    return dict(raw) if isinstance(raw, Mapping) else {}


def _runtime_effects(
    name: str,
    tool: Any,
    *,
    owner_effects: tuple[OperationEffect, ...],
) -> tuple[OperationEffect, ...]:
    normalized = name.casefold()
    owner = set(owner_effects)
    external = OperationEffect.EXTERNAL in owner
    read_only = _annotation(tool, "readOnlyHint") or normalized.startswith(
        (
            "read_",
            "list_",
            "get_",
            "search_",
            "inspect_",
            "describe_",
            "recommend_",
            "load_",
            "evaluate_",
        )
    ) or normalized in {
        "kis_health",
        "kis_provider_status",
        "skill_telemetry_report",
    }

    if external:
        effects = {OperationEffect.EXTERNAL}
        if read_only:
            effects.add(OperationEffect.READ_ONLY)
        return tuple(sorted(effects, key=lambda item: item.value))

    if read_only:
        return (OperationEffect.READ_ONLY,)
    if normalized.startswith(("kis_quarantine_", "delete_", "remove_")):
        return (OperationEffect.QUARANTINE,)
    if normalized == "record_skill_outcome":
        return (OperationEffect.LOCAL_CHANGE,)
    if normalized.startswith(
        ("start_process", "interact_with_process", "kill_process", "terminate_", "stop_")
    ):
        return (OperationEffect.PROCESS,)
    if normalized.startswith(
        ("write_", "edit_", "create_", "move_", "restore_", "improve_", "set_", "refresh_")
    ):
        return (OperationEffect.LOCAL_CHANGE,)
    if normalized in {"review_change_with_agent", "benchmark_nvidia_model"}:
        return (OperationEffect.READ_ONLY, OperationEffect.EXTERNAL)
    return (OperationEffect.PROCESS,)


def _capabilities(name: str, effects: tuple[OperationEffect, ...]) -> tuple[str, ...]:
    normalized = name.casefold()
    values = {f"operation.{normalized}"}
    if "skill" in normalized:
        values.add("skills.catalogue")
    if "file" in normalized or "directory" in normalized:
        values.add("filesystem.local")
    if "search" in normalized:
        values.add("search.local")
    if OperationEffect.PROCESS in effects:
        values.add("process.local")
    if OperationEffect.EXTERNAL in effects:
        values.add("external.operation")
    if "git" in normalized or "github" in normalized:
        values.add("repository.git")
    return tuple(sorted(values))


def capability_control_contribution() -> CapabilityContribution:
    operations = (
        ("search_capabilities", "Search the normalized capability catalogue.", OperationEffect.READ_ONLY),
        ("describe_capability", "Describe one capability, contribution, operation, or workflow.", OperationEffect.READ_ONLY),
        ("recommend_workflow", "Recommend complete workflows for one user task.", OperationEffect.READ_ONLY),
        ("execute_read_action", "Execute one eligible read-only long-tail operation.", OperationEffect.READ_ONLY),
        ("execute_change_action", "Execute one eligible local change or process operation.", OperationEffect.LOCAL_CHANGE),
        ("execute_external_action", "Execute one eligible external operation without bypassing approval.", OperationEffect.EXTERNAL),
    )
    descriptors = tuple(
        OperationDescriptor(
            operation_id=f"capability-control.{name}",
            name=name,
            description=description,
            capabilities=(f"capability.{name}",),
            effects=(effect,),
            dependencies=(),
            exposure=ExposurePolicy(mode=ExposureMode.DIRECT, priority=100),
            quality=default_quality(context_cost=5, reliability=95, workflow_integration=100),
        )
        for name, description, effect in operations
    )
    virtual_descriptors = (
        OperationDescriptor(
            operation_id="capability-control.kis-github-publish-registered-commit",
            name="kis_github_publish_registered_commit",
            description="Publish one immutable local commit to its registered GitHub branch with exact ref verification.",
            capabilities=("operation.kis_github_publish_registered_commit",),
            effects=(OperationEffect.EXTERNAL,),
            dependencies=(),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=92),
            quality=default_quality(context_cost=20, reversibility=70, reliability=90, workflow_integration=95),
            approval_required=True,
            tags=("registered-github", "virtual"),
            input_schema=REGISTERED_GITHUB_OPERATION_SCHEMAS["kis_github_publish_registered_commit"],
        ),
        OperationDescriptor(
            operation_id="capability-control.kis-github-reconcile-registered-commit",
            name="kis_github_reconcile_registered_commit",
            description="Publish one registered review branch by preserving the exact source tree on a verified tree-equivalent remote default-branch parent.",
            capabilities=("operation.kis_github_reconcile_registered_commit",),
            effects=(OperationEffect.EXTERNAL,),
            dependencies=(),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=92),
            quality=default_quality(context_cost=20, reversibility=70, reliability=90, workflow_integration=95),
            approval_required=True,
            tags=("registered-github", "virtual"),
            input_schema=REGISTERED_GITHUB_OPERATION_SCHEMAS["kis_github_reconcile_registered_commit"],
        ),
        OperationDescriptor(
            operation_id="capability-control.kis-github-create-registered-pull-request",
            name="kis_github_create_registered_pull_request",
            description="Create one open pull request for an exact registered review-branch head after verifying the remote default branch.",
            capabilities=("operation.kis_github_create_registered_pull_request",),
            effects=(OperationEffect.EXTERNAL,),
            dependencies=(),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=92),
            quality=default_quality(context_cost=20, reversibility=70, reliability=90, workflow_integration=95),
            approval_required=True,
            tags=("registered-github", "virtual"),
            input_schema=REGISTERED_GITHUB_OPERATION_SCHEMAS["kis_github_create_registered_pull_request"],
        ),
        OperationDescriptor(
            operation_id="capability-control.kis-github-configure-registered-repository",
            name="kis_github_configure_registered_repository",
            description="Configure one registered GitHub repository for merge-commit-only landing with KIS-owned exact branch cleanup.",
            capabilities=("operation.kis_github_configure_registered_repository",),
            effects=(OperationEffect.EXTERNAL,),
            dependencies=(),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=92),
            quality=default_quality(context_cost=15, reversibility=90, reliability=90, workflow_integration=95),
            approval_required=True,
            tags=("registered-github", "virtual"),
            input_schema=REGISTERED_GITHUB_OPERATION_SCHEMAS["kis_github_configure_registered_repository"],
        ),
        OperationDescriptor(
            operation_id="capability-control.kis-github-commission-registered-project-schema",
            name="kis_github_commission_registered_project_schema",
            description="Provision and verify one centrally registered GitHub Project against the canonical Work Management schema, optionally limiting mutation and verification to canonical fields, without exposing arbitrary Project administration.",
            capabilities=("operation.kis_github_commission_registered_project_schema",),
            effects=(OperationEffect.EXTERNAL,),
            dependencies=(),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=94),
            quality=default_quality(context_cost=15, reversibility=70, reliability=95, workflow_integration=100),
            approval_required=True,
            tags=("registered-github", "virtual", "project-schema"),
            input_schema=REGISTERED_GITHUB_OPERATION_SCHEMAS["kis_github_commission_registered_project_schema"],
        ),
        OperationDescriptor(
            operation_id="capability-control.kis-github-merge-registered-pull-request",
            name="kis_github_merge_registered_pull_request",
            description="Merge one registered-repository pull request only at its explicitly approved head SHA.",
            capabilities=("operation.kis_github_merge_registered_pull_request",),
            effects=(OperationEffect.EXTERNAL,),
            dependencies=(),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=92),
            quality=default_quality(context_cost=20, reversibility=70, reliability=90, workflow_integration=95),
            approval_required=True,
            tags=("registered-github", "virtual"),
            input_schema=REGISTERED_GITHUB_OPERATION_SCHEMAS["kis_github_merge_registered_pull_request"],
        ),
        OperationDescriptor(
            operation_id="capability-control.kis-github-refresh-registered-default-branch",
            name="kis_github_refresh_registered_default_branch",
            description="Refresh the registered default-branch tracking ref from verified GitHub truth.",
            capabilities=("operation.kis_github_refresh_registered_default_branch",),
            effects=(OperationEffect.EXTERNAL, OperationEffect.LOCAL_CHANGE),
            dependencies=(),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=92),
            quality=default_quality(context_cost=15, reversibility=95, reliability=95, workflow_integration=100),
            approval_required=True,
            tags=("registered-github", "virtual"),
            input_schema=REGISTERED_GITHUB_TRACKING_OPERATION_SCHEMAS["kis_github_refresh_registered_default_branch"],
        ),
        OperationDescriptor(
            operation_id="capability-control.kis-acquire-registered-evidence",
            name="kis_acquire_registered_evidence",
            description="Acquire external evidence only for an authorized registered project/profile and immutable consumer recipe hash through import-isolate.",
            capabilities=("operation.kis_acquire_registered_evidence",),
            effects=(OperationEffect.EXTERNAL,),
            dependencies=(),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=94),
            quality=default_quality(context_cost=15, reversibility=95, reliability=90, workflow_integration=100),
            approval_required=True,
            tags=("registered-acquisition", "virtual"),
            input_schema=REGISTERED_ACQUISITION_OPERATION_SCHEMA,
        ),
    )
    merge_queue_specs = (
        (
            "kis_github_merge_queue_status",
            "Read the registered speculative landing queue and compare its generation base with live GitHub truth.",
            (OperationEffect.EXTERNAL, OperationEffect.READ_ONLY),
            False,
        ),
        (
            "kis_github_merge_queue_enqueue",
            "Enqueue one registered pull request at an explicitly frozen head SHA after recomputing exact Work Management merge readiness from supplied record and trace evidence.",
            (OperationEffect.EXTERNAL, OperationEffect.LOCAL_CHANGE),
            True,
        ),
        (
            "kis_github_merge_queue_reconcile",
            "Reconcile exact queue identity, cumulative candidates, and candidate Actions evidence for one registered repository.",
            (OperationEffect.EXTERNAL, OperationEffect.LOCAL_CHANGE),
            True,
        ),
        (
            "kis_github_merge_queue_dequeue",
            "Dequeue one registered pull request only at its frozen head SHA and invalidate its queue generation.",
            (OperationEffect.EXTERNAL, OperationEffect.LOCAL_CHANGE),
            True,
        ),
        (
            "kis_github_merge_queue_land",
            "Advance the registered default branch only from the queue generation's exact base to an ALLGREEN cumulative candidate after fresh Work Management readiness is recomputed for every selected pull request.",
            (OperationEffect.EXTERNAL, OperationEffect.LOCAL_CHANGE),
            True,
        ),
    )
    merge_queue_descriptors = tuple(
        OperationDescriptor(
            operation_id=f"capability-control.{name.replace('_', '-')}",
            name=name,
            description=description,
            capabilities=(f"operation.{name}",),
            effects=effects,
            dependencies=(),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=94),
            quality=default_quality(
                context_cost=20,
                reversibility=85,
                reliability=95,
                workflow_integration=100,
            ),
            approval_required=approval_required,
            tags=("registered-github", "virtual", "merge-queue"),
            input_schema=REGISTERED_GITHUB_MERGE_QUEUE_OPERATION_SCHEMAS[name],
        )
        for name, description, effects, approval_required in merge_queue_specs
    )
    descriptors = (*descriptors, *virtual_descriptors, *merge_queue_descriptors)
    contribution_id = "capability-control"
    return CapabilityContribution(
        contribution_id=contribution_id,
        domain=CapabilityDomain.WORKFLOW,
        category="capability-experience",
        capabilities=tuple(item.capabilities[0] for item in descriptors),
        operations=descriptors,
        dependencies=(),
        effects=(OperationEffect.READ_ONLY, OperationEffect.LOCAL_CHANGE, OperationEffect.EXTERNAL),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id=contribution_id,
            state=ReadinessState.READY,
            summary="Capability discovery and dispatch are ready.",
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DIRECT, priority=100),
        quality=default_quality(context_cost=5, reliability=95, workflow_integration=100),
    )


def augment_with_runtime_surface(
    contributions: Iterable[CapabilityContribution],
    tools: Iterable[Any],
    provider_namespaces: dict[str, str],
) -> tuple[CapabilityContribution, ...]:
    items = {item.contribution_id: item for item in contributions}
    runtime_tools = tuple(tools)
    tools_by_name = {
        str(getattr(tool, "name", "")): tool
        for tool in runtime_tools
        if getattr(tool, "name", None)
    }
    actual_names = set(tools_by_name)
    for contribution_id, contribution in tuple(items.items()):
        if contribution_id == "capability-control":
            continue
        operations = tuple(
            replace(operation, input_schema=_input_schema(tools_by_name[operation.name]))
            if operation.name in actual_names
            else operation
            if "virtual" in operation.tags
            else replace(
                operation,
                enabled=False,
                exposure=ExposurePolicy(
                    mode=ExposureMode.STATUS_ONLY,
                    priority=operation.exposure.priority,
                    status_visible=True,
                    explicit_request_allowed=False,
                ),
            )
            for operation in contribution.operations
        )
        if operations != contribution.operations:
            items[contribution_id] = replace(contribution, operations=operations)
    known_names = {
        operation.name for contribution in items.values() for operation in contribution.operations
    }
    runtime_operations: list[OperationDescriptor] = []
    runtime_capabilities: set[str] = set()
    runtime_effects: set[OperationEffect] = set()

    for tool in sorted(runtime_tools, key=lambda item: str(getattr(item, "name", ""))):
        name = str(getattr(tool, "name", ""))
        if not name or name in known_names:
            continue
        owner_id = None
        owner_effects: tuple[OperationEffect, ...] = ()
        for provider_id, namespace in provider_namespaces.items():
            if name.startswith(f"{namespace}_"):
                owner_id = f"provider.{provider_id}"
                owner = items.get(owner_id)
                owner_effects = owner.effects if owner is not None else ()
                break
        effects = _runtime_effects(name, tool, owner_effects=owner_effects)
        capabilities = _capabilities(name, effects)
        operation = OperationDescriptor(
            operation_id=f"runtime.{name}",
            name=name,
            description=str(getattr(tool, "description", "") or f"Run {name}."),
            capabilities=capabilities,
            effects=effects,
            dependencies=(),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=50),
            quality=default_quality(
                context_cost=35,
                reversibility=90 if OperationEffect.READ_ONLY in effects else 70,
                reliability=85,
                workflow_integration=70,
            ),
            approval_required=False,
            authentication_preflight=any(term in name.casefold() for term in ("auth", "status", "health", "preflight")),
            input_schema=_input_schema(tool),
        )
        if owner_id is not None and owner_id in items:
            current = items[owner_id]
            items[owner_id] = replace(
                current,
                operations=tuple((*current.operations, operation)),
                capabilities=tuple(sorted(set((*current.capabilities, *capabilities)))),
                effects=tuple(sorted(set((*current.effects, *effects)), key=lambda item: item.value)),
            )
        else:
            runtime_operations.append(operation)
            runtime_capabilities.update(capabilities)
            runtime_effects.update(effects)

    if runtime_operations:
        contribution_id = "runtime-surface"
        items[contribution_id] = CapabilityContribution(
            contribution_id=contribution_id,
            domain=CapabilityDomain.TOOL,
            category="runtime-surface",
            capabilities=tuple(sorted(runtime_capabilities)),
            operations=tuple(runtime_operations),
            dependencies=(),
            effects=tuple(sorted(runtime_effects, key=lambda item: item.value)),
            readiness_probe=lambda: ReadinessSnapshot(
                contribution_id=contribution_id,
                state=ReadinessState.READY,
                summary="Registered runtime operations are available.",
            ),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=50),
            quality=default_quality(context_cost=35, workflow_integration=70),
        )
    return tuple(items[key] for key in sorted(items))


__all__ = ["augment_with_runtime_surface", "capability_control_contribution"]
