from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from .contracts import (
    EvidenceReference,
    EvidenceState,
    PromotionReadyHandoff,
    TaskHandoffContract,
)
from .evidence import resolve_evidence

CandidateInvoker = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


def derive_promotion_ready(
    contract: TaskHandoffContract,
    *,
    source_commit_sha: str,
    execution: Mapping[str, Any],
    evidence: tuple[EvidenceReference, ...],
    observed_inputs: Mapping[str, str],
    candidate_identity: Mapping[str, Any],
) -> PromotionReadyHandoff:
    mandatory = {"review_closed"}
    if any(surface.casefold() == "mcp" for surface in contract.affected_surfaces):
        mandatory.add("live_candidate_verification")
    required_kinds = tuple(dict.fromkeys((*contract.obligations, *sorted(mandatory))))
    resolutions = resolve_evidence(
        evidence,
        required_kinds=required_kinds,
        observed_inputs=observed_inputs,
        phase="promotion",
    )
    pending = tuple(item.kind for item in resolutions if item.state is not EvidenceState.VALID)
    if pending:
        detail = ", ".join(f"{item.kind}:{item.state.value}" for item in resolutions if item.state is not EvidenceState.VALID)
        raise ValueError(f"PROMOTION_NOT_READY: {detail}")
    if execution.get("contract") != "change-execution-result-v2" or execution.get("status") != "passed":
        raise ValueError("PROMOTION_NOT_READY: implementation execution evidence has not passed")
    expected_candidate = {
        "work_id": contract.work_id,
        "contract_fingerprint": contract.contract_fingerprint,
        "source_identity": contract.source_identity,
    }
    for key, expected in expected_candidate.items():
        if candidate_identity.get(key) != expected:
            raise ValueError(f"PROMOTION_NOT_READY: candidate identity mismatch for {key}")
    if not isinstance(candidate_identity.get("server_instance_id"), str) or not candidate_identity["server_instance_id"]:
        raise ValueError("PROMOTION_NOT_READY: candidate server instance identity is missing")
    if "live_candidate_verification" in required_kinds:
        live = next(item for item in evidence if item.kind == "live_candidate_verification")
        expected_live_inputs = {
            "source_commit": source_commit_sha,
            "server_instance_id": str(candidate_identity["server_instance_id"]),
            "contract_fingerprint": contract.contract_fingerprint,
        }
        mismatched = tuple(
            key for key, expected in expected_live_inputs.items()
            if live.validity_inputs.get(key) != expected
        )
        if mismatched:
            raise ValueError(
                "PROMOTION_NOT_READY: live candidate proof identity mismatch: "
                + ", ".join(mismatched)
            )
    return PromotionReadyHandoff(
        work_id=contract.work_id,
        change_id=contract.change_id or "unassigned",
        contract_fingerprint=contract.contract_fingerprint,
        source_commit_sha=source_commit_sha,
        candidate_identity=candidate_identity,
        execution=execution,
        evidence=evidence,
        satisfied_obligations=required_kinds,
    )


async def verify_live_candidate(
    contract: TaskHandoffContract,
    *,
    expected_identity: Mapping[str, Any],
    scenarios: tuple[Mapping[str, Any], ...],
    invoker: CandidateInvoker,
) -> dict[str, Any]:
    identity = await invoker("identity", {"port": contract.candidate_port})
    for key in ("work_id", "contract_fingerprint", "source_identity", "server_instance_id"):
        expected = expected_identity.get(key)
        if expected is None or identity.get(key) != expected:
            raise ValueError(f"CANDIDATE_IDENTITY_MISMATCH: {key}")
    outcomes: list[dict[str, Any]] = []
    for scenario in scenarios:
        result = await invoker("mcp", {"port": contract.candidate_port, **dict(scenario)})
        outcomes.append(result)
        if result.get("status") != "passed":
            raise ValueError(f"LIVE_CANDIDATE_VERIFICATION_FAILED: {scenario.get('id', 'scenario')}")
    return {
        "contract": "live-candidate-verification-v1",
        "status": "passed",
        "candidate_identity": dict(identity),
        "scenario_count": len(outcomes),
        "outcomes": outcomes,
    }


__all__ = ["derive_promotion_ready", "verify_live_candidate"]
