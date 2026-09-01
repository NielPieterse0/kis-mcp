from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import (
    EvidenceReference,
    EvidenceResolution,
    EvidenceState,
    ObligationPhase,
    TaskObligation,
    fingerprint,
)

_PHASE_ORDER = {
    "implementation": 0,
    "review": 1,
    "candidate": 2,
    "promotion": 2,
    "pull_request": 3,
    "documentation": 4,
    "commissioning": 5,
    "completion": 6,
    "post_merge": 6,
}

_CONDITIONAL_OBLIGATIONS = {
    TaskObligation.LIVE_CANDIDATE_VERIFICATION: "mcp_surface",
    TaskObligation.PROVIDER_PROOF: "provider_required",
    TaskObligation.DOCUMENTATION: "documentation_required",
    TaskObligation.COMMISSIONING: "commissioning_required",
}


def resolve_evidence(
    references: tuple[EvidenceReference, ...],
    *,
    required_kinds: tuple[str, ...],
    observed_inputs: Mapping[str, str],
    phase: str = "promotion",
) -> tuple[EvidenceResolution, ...]:
    by_kind: dict[str, list[EvidenceReference]] = {}
    for item in references:
        by_kind.setdefault(item.kind, []).append(item)
    results: list[EvidenceResolution] = []
    current_phase = _PHASE_ORDER.get(phase, -1)
    for kind in required_kinds:
        candidates = by_kind.get(kind, [])
        if not candidates:
            results.append(EvidenceResolution(kind, kind, EvidenceState.MISSING, "required evidence is absent"))
            continue
        if len(candidates) != 1:
            results.append(EvidenceResolution(
                kind, kind, EvidenceState.INVALID,
                f"required evidence kind is ambiguous: {len(candidates)} receipts",
            ))
            continue
        item = candidates[0]
        applicable = _PHASE_ORDER.get(item.applicable_phase, 0)
        if current_phase < applicable:
            results.append(EvidenceResolution(item.evidence_id, kind, EvidenceState.NOT_YET_APPLICABLE, f"applies at {item.applicable_phase}", item.receipt_ref))
            continue
        changed = tuple(
            key for key, expected in item.validity_inputs.items()
            if observed_inputs.get(key) != expected
        )
        if changed:
            results.append(EvidenceResolution(
                item.evidence_id, kind, EvidenceState.INVALID,
                "validity inputs changed: " + ", ".join(sorted(changed)),
                item.receipt_ref,
            ))
            continue
        results.append(EvidenceResolution(
            item.evidence_id, kind, EvidenceState.VALID,
            "all declared validity inputs match", item.receipt_ref,
        ))
    return tuple(results)


def minimum_rerun(resolutions: tuple[EvidenceResolution, ...]) -> tuple[str, ...]:
    return tuple(
        item.kind for item in resolutions
        if item.state in {EvidenceState.INVALID, EvidenceState.MISSING}
    )


def required_obligations(
    obligations: Sequence[TaskObligation | str],
    *,
    phase: ObligationPhase | str,
    conditions: Mapping[str, bool],
) -> tuple[TaskObligation, ...]:
    current = ObligationPhase(phase)
    order = tuple(ObligationPhase)
    required: list[TaskObligation] = []
    for raw in obligations:
        obligation = TaskObligation(raw)
        if order.index(obligation.phase) > order.index(current):
            continue
        condition = _CONDITIONAL_OBLIGATIONS.get(obligation)
        if condition is not None:
            if condition not in conditions:
                raise ValueError(f"OBLIGATION_CONDITION_UNRESOLVED: {condition}")
            if conditions[condition] is not True:
                continue
        required.append(obligation)
    return tuple(required)


def validate_mcp_tool_schemas(
    expected: Mapping[str, Mapping[str, Any]],
    published: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    proof: dict[str, str] = {}
    for tool_name, contract in expected.items():
        observed = published.get(tool_name)
        if not isinstance(observed, Mapping):
            raise ValueError(f"MCP_TOOL_SCHEMA_MISSING: {tool_name}")
        for field in ("inputSchema", "outputSchema"):
            wanted = contract.get(field)
            actual = observed.get(field)
            if not isinstance(wanted, Mapping):
                raise ValueError(f"MCP_EXPECTED_SCHEMA_INVALID: {tool_name}.{field}")
            if not isinstance(actual, Mapping):
                raise ValueError(f"MCP_TOOL_SCHEMA_MISSING: {tool_name}.{field}")
            if fingerprint(wanted) != fingerprint(actual):
                raise ValueError(f"MCP_TOOL_SCHEMA_MISMATCH: {tool_name}.{field}")
        proof[tool_name] = fingerprint({
            "inputSchema": contract["inputSchema"],
            "outputSchema": contract["outputSchema"],
        })
    return proof


def validate_effect_safe_scenarios(
    scenarios: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    if len(scenarios) != len(outcomes):
        raise ValueError("LIVE_EFFECT_EVIDENCE_MISMATCH: scenario/outcome count differs")
    proofs: list[str] = []
    for scenario, outcome in zip(scenarios, outcomes, strict=True):
        effect = str(scenario.get("effect", "read_only"))
        if effect in {"read_only", "none"}:
            continue
        boundary = scenario.get("effect_boundary")
        if not isinstance(boundary, Mapping):
            raise ValueError("LIVE_EFFECT_BOUNDARY_REQUIRED: mutating/external scenario")
        fixture_id = boundary.get("fixture_id")
        if boundary.get("disposable") is not True or not isinstance(fixture_id, str) or not fixture_id:
            raise ValueError("LIVE_EFFECT_BOUNDARY_INVALID: disposable fixture required")
        cleanup = outcome.get("cleanup")
        recovery = outcome.get("recovery")
        evidence = cleanup if isinstance(cleanup, Mapping) else recovery
        if not isinstance(evidence, Mapping) or evidence.get("status") not in {"passed", "applied", "satisfied"}:
            raise ValueError("LIVE_EFFECT_CLEANUP_EVIDENCE_REQUIRED: cleanup/recovery proof missing")
        proofs.append(fingerprint({
            "effect": effect,
            "fixture_id": fixture_id,
            "boundary": dict(boundary),
            "cleanup_or_recovery": dict(evidence),
        }))
    return tuple(proofs)


__all__ = [
    "minimum_rerun", "required_obligations", "resolve_evidence",
    "validate_effect_safe_scenarios", "validate_mcp_tool_schemas",
]
