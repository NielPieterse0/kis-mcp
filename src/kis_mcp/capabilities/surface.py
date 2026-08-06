from __future__ import annotations

import re
from dataclasses import replace
from typing import Any, Iterable

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


def _runtime_effects(name: str, tool: Any, *, external: bool) -> tuple[OperationEffect, ...]:
    normalized = name.casefold()
    effects: set[OperationEffect] = set()
    if external:
        effects.add(OperationEffect.EXTERNAL)
    if _annotation(tool, "readOnlyHint") or normalized.startswith(
        ("read_", "list_", "get_", "search_", "inspect_", "describe_", "recommend_", "load_", "evaluate_")
    ) or normalized in {"kis_health", "kis_provider_status"}:
        effects.add(OperationEffect.READ_ONLY)
    if any(term in normalized for term in ("quarantine", "delete_", "remove_")):
        effects.add(OperationEffect.QUARANTINE)
    if normalized.startswith(("write_", "edit_", "create_", "move_", "restore_", "improve_", "set_", "refresh_")):
        effects.add(OperationEffect.LOCAL_CHANGE)
    if any(term in normalized for term in ("process", "command", "terminate", "kill_", "stop_")):
        effects.add(OperationEffect.PROCESS)
    if normalized == "review_change_with_agent":
        effects.update({OperationEffect.READ_ONLY, OperationEffect.EXTERNAL})
    if not effects:
        effects.add(OperationEffect.PROCESS)
    return tuple(sorted(effects, key=lambda item: item.value))


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
    known_names = {
        operation.name for contribution in items.values() for operation in contribution.operations
    }
    runtime_operations: list[OperationDescriptor] = []
    runtime_capabilities: set[str] = set()
    runtime_effects: set[OperationEffect] = set()

    for tool in sorted(tools, key=lambda item: str(getattr(item, "name", ""))):
        name = str(getattr(tool, "name", ""))
        if not name or name in known_names:
            continue
        owner_id = None
        external = False
        for provider_id, namespace in provider_namespaces.items():
            if name.startswith(f"{namespace}_"):
                owner_id = f"provider.{provider_id}"
                external = True
                break
        effects = _runtime_effects(name, tool, external=external)
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
            approval_required=any(term in name.casefold() for term in ("merge", "publish", "deploy", "send_email")),
            authentication_preflight=any(term in name.casefold() for term in ("auth", "status", "health", "preflight")),
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
