from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from kis_mcp.commissioning.runner import FrozenCommissioningExecution


class ReadInvoker(Protocol):
    async def read(self, operation: str, arguments: dict[str, Any]) -> Any: ...


AncestorCheck = Callable[[Path, str, str], bool]
_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class RuntimeGenerationGate:
    ready: bool
    code: str
    source_revision: str | None = None


@dataclass(frozen=True, slots=True)
class ProbeOutcome:
    passed: bool
    code: str
    operation: str
    evidence: dict[str, Any]
    response_fingerprint: str


def _canonical_fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()

def _normalized_instance(value: Any) -> str:
    selected = str(value or "").strip().casefold()
    return {
        "operation": "kis-op",
        "op": "kis-op",
        "kis-op": "kis-op",
        "development": "kis-dev",
        "dev": "kis-dev",
        "kis-dev": "kis-dev",
    }.get(selected, selected)


def _git_is_ancestor(root: Path, merge_sha: str, source_revision: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", merge_sha, source_revision],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise RuntimeError("runtime ancestry check failed")


async def runtime_generation_gate(
    frozen: FrozenCommissioningExecution,
    invoker: ReadInvoker,
    *,
    project_id: str,
    ancestor_check: AncestorCheck = _git_is_ancestor,
) -> RuntimeGenerationGate:
    if frozen.refresh_rule == "none":
        return RuntimeGenerationGate(True, "refresh_not_required")
    health = await invoker.read("kis_health", {})
    if not isinstance(health, Mapping) or health.get("ready") is not True:
        return RuntimeGenerationGate(False, "runtime_not_ready")
    if _normalized_instance(health.get("runtime_instance")) != frozen.runtime_instance:
        return RuntimeGenerationGate(False, "runtime_instance_mismatch")
    source_revision = health.get("source_revision")
    if (
        not isinstance(source_revision, str)
        or _SHA.fullmatch(source_revision.casefold()) is None
    ):
        return RuntimeGenerationGate(False, "runtime_source_revision_invalid")
    source_revision = source_revision.casefold()
    project = await invoker.read("kis_project_status", {"project_id": project_id})
    if not isinstance(project, Mapping) or not isinstance(project.get("project"), Mapping):
        return RuntimeGenerationGate(False, "project_status_invalid", source_revision)
    local_root = project["project"].get("local_root")
    if not isinstance(local_root, str) or not local_root:
        return RuntimeGenerationGate(False, "project_root_unavailable", source_revision)
    if not ancestor_check(Path(local_root), frozen.merge_sha, source_revision):
        return RuntimeGenerationGate(False, "runtime_refresh_required", source_revision)
    return RuntimeGenerationGate(True, "runtime_generation_current", source_revision)


def _outcome(operation: str, passed: bool, code: str, evidence: dict[str, Any]) -> ProbeOutcome:
    return ProbeOutcome(
        passed=passed,
        code=code,
        operation=operation,
        evidence=evidence,
        response_fingerprint=_canonical_fingerprint(evidence),
    )


async def _board_probe(
    frozen: FrozenCommissioningExecution,
    invoker: ReadInvoker,
    project_id: str,
    execution_owner: str,
) -> ProbeOutcome:
    operation = "project_management_board_data"
    value = await invoker.read(
        operation,
        {
            "project_id": project_id,
            "include_history": False,
            "query": str(frozen.commissioning_issue),
            "owner": execution_owner,
            "group_by": "state",
            "item_limit": 1000,
        },
    )
    result = value.get("result") if isinstance(value, Mapping) else None
    cards = result.get("cards") if isinstance(result, Mapping) else None
    complete = (
        isinstance(value, Mapping)
        and isinstance(value.get("provenance"), Mapping)
        and value["provenance"].get("complete") is True
        and isinstance(result, Mapping)
        and result.get("complete") is True
        and result.get("truncated") is False
        and isinstance(cards, list)
    )
    matches = [
        card for card in cards or []
        if isinstance(card, Mapping)
        and card.get("number") == frozen.commissioning_issue
        and card.get("work_state") == "active"
        and card.get("execution_owner") == execution_owner
    ]
    evidence = {"complete": complete, "matching_cards": len(matches)}
    return _outcome(operation, complete and len(matches) == 1, "board_claim_verified" if complete and len(matches) == 1 else "board_claim_invalid", evidence)


async def _gateway_probe(
    frozen: FrozenCommissioningExecution,
    invoker: ReadInvoker,
) -> ProbeOutcome:
    operation = "kis_health"
    value = await invoker.read(operation, {})
    passed = (
        isinstance(value, Mapping)
        and value.get("ready") is True
        and _normalized_instance(value.get("runtime_instance")) == frozen.runtime_instance
        and isinstance(value.get("source_revision"), str)
        and len(value["source_revision"]) == 40
    )
    evidence = {
        "ready": value.get("ready") if isinstance(value, Mapping) else None,
        "runtime_instance": _normalized_instance(value.get("runtime_instance")) if isinstance(value, Mapping) else None,
        "source_revision": value.get("source_revision") if isinstance(value, Mapping) else None,
    }
    return _outcome(operation, passed, "gateway_ready" if passed else "gateway_not_ready", evidence)


async def _housekeeping_probe(
    frozen: FrozenCommissioningExecution,
    invoker: ReadInvoker,
) -> ProbeOutcome:
    operation = "kis_housekeeping_status"
    value = await invoker.read(operation, {})
    targets = value.get("targets") if isinstance(value, Mapping) else None
    schedulers = (
        isinstance(targets, list)
        and bool(targets)
        and all(isinstance(item, Mapping) and item.get("scheduler_active") is True for item in targets)
    )
    passed = (
        isinstance(value, Mapping)
        and value.get("active") is True
        and _normalized_instance(value.get("current_instance")) == frozen.runtime_instance
        and schedulers
    )
    evidence = {
        "active": value.get("active") if isinstance(value, Mapping) else None,
        "current_instance": _normalized_instance(value.get("current_instance")) if isinstance(value, Mapping) else None,
        "scheduler_targets_ready": schedulers,
    }
    return _outcome(operation, passed, "housekeeping_ready" if passed else "housekeeping_not_ready", evidence)


async def _provider_probe(invoker: ReadInvoker) -> ProbeOutcome:
    operation = "kis_provider_status"
    value = await invoker.read(operation, {})
    health = value.get("platform_health") if isinstance(value, Mapping) else None
    passed = (
        isinstance(health, Mapping)
        and health.get("state") == "ready"
        and health.get("unavailable_count") == 0
    )
    evidence = {
        "state": health.get("state") if isinstance(health, Mapping) else None,
        "unavailable_count": health.get("unavailable_count") if isinstance(health, Mapping) else None,
    }
    return _outcome(operation, passed, "provider_platform_ready" if passed else "provider_platform_not_ready", evidence)


async def _observer_probe(
    frozen: FrozenCommissioningExecution,
    invoker: ReadInvoker,
) -> ProbeOutcome:
    operation = "kis_post_merge_commissioning_status"
    value = await invoker.read(operation, {})
    targets = value.get("targets") if isinstance(value, Mapping) else None
    target = next(
        (
            item for item in targets or []
            if isinstance(item, Mapping)
            and str(item.get("repository", "")).casefold() == frozen.repository.casefold()
        ),
        None,
    )
    passed = (
        isinstance(value, Mapping)
        and value.get("active") is True
        and _normalized_instance(value.get("current_instance")) == frozen.runtime_instance
        and isinstance(target, Mapping)
        and target.get("checkpoint_state") == "ready"
        and target.get("freshness") == "fresh"
        and target.get("scheduler_active") is True
    )
    evidence = {
        "active": value.get("active") if isinstance(value, Mapping) else None,
        "checkpoint_state": target.get("checkpoint_state") if isinstance(target, Mapping) else None,
        "freshness": target.get("freshness") if isinstance(target, Mapping) else None,
        "scheduler_active": target.get("scheduler_active") if isinstance(target, Mapping) else None,
    }
    return _outcome(operation, passed, "observer_ready" if passed else "observer_not_ready", evidence)


async def _work_contract_probe(invoker: ReadInvoker) -> ProbeOutcome:
    operation = "project_management_contract"
    value = await invoker.read(operation, {})
    canonical = value.get("canonical_contracts") if isinstance(value, Mapping) else None
    lifecycle = canonical.get("work_lifecycle_operations") if isinstance(canonical, Mapping) else None
    domains = lifecycle.get("verification_domains") if isinstance(lifecycle, Mapping) else None
    ids = {
        str(item.get("id")): str(item.get("field"))
        for item in domains or []
        if isinstance(item, Mapping)
    }
    passed = (
        isinstance(value, Mapping)
        and value.get("schema_version") == 1
        and ids.get("source_verification") == "Verification"
        and ids.get("live_verification") == "Live Verification"
    )
    evidence = {
        "schema_version": value.get("schema_version") if isinstance(value, Mapping) else None,
        "verification_domains": ids,
    }
    return _outcome(operation, passed, "work_contract_ready" if passed else "work_contract_invalid", evidence)


async def execute_probe(
    frozen: FrozenCommissioningExecution,
    invoker: ReadInvoker,
    *,
    project_id: str,
    execution_owner: str,
) -> ProbeOutcome:
    if frozen.probe_id == "coordinator-work-board":
        return await _board_probe(frozen, invoker, project_id, execution_owner)
    if frozen.probe_id == "gateway-health":
        return await _gateway_probe(frozen, invoker)
    if frozen.probe_id == "housekeeping-status":
        return await _housekeeping_probe(frozen, invoker)
    if frozen.probe_id == "provider-status":
        return await _provider_probe(invoker)
    if frozen.probe_id == "post-merge-observer-status":
        return await _observer_probe(frozen, invoker)
    if frozen.probe_id == "work-management-contract":
        return await _work_contract_probe(invoker)
    raise ValueError("unsupported commissioning probe_id")


__all__ = [
    "ProbeOutcome",
    "RuntimeGenerationGate",
    "execute_probe",
    "runtime_generation_gate",
]
