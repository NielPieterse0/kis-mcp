from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from kis_mcp.workflows.coordinator import (
    PlannerRequest,
    PlannerService,
    PlannerTask,
    WorkPacketService,
)
from kis_mcp.workflows.coordinator.models import ReservationAdmissionError
from kis_mcp.workflows.coordinator.provenance import (
    GitHubProvenanceService,
    validate_delivery_provenance,
    validate_provenance_evidence,
)

HEAD = "a" * 40
MERGE = "b" * 40


def _claim(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "provider": "github",
        "repository": "NielPieterse0/kis-mcp",
        "issue_number": 413,
        "pull_number": 427,
        "head_sha": HEAD,
        "merge_sha": None,
    }
    value.update(overrides)
    return value


def _resolver(claim: dict[str, object]) -> dict[str, object]:
    return _claim(repository="nielpieterse0/kis-mcp")


def test_live_provider_identity_rejects_issue_pr_and_stale_head_mismatch() -> None:
    service = GitHubProvenanceService(resolve_provider=_resolver)

    with pytest.raises(ReservationAdmissionError, match="GITHUB_PROVENANCE_MISMATCH"):
        service.verify(_claim(issue_number=88))
    with pytest.raises(ReservationAdmissionError, match="GITHUB_PROVENANCE_MISMATCH"):
        service.verify(_claim(head_sha="c" * 40))

    verified = service.verify(_claim())
    assert verified["status"] == "verified"
    assert verified["tuple"] == _claim(repository="nielpieterse0/kis-mcp")
    assert verified["claim_sha256"]


def test_reused_pr_narrative_is_quarantined_and_exact_duplicates_deduplicate() -> None:
    service = GitHubProvenanceService(resolve_provider=_resolver)
    result = service.aggregate((_claim(), _claim(), _claim(issue_number=88)))

    assert len(result["accepted"]) == 1
    assert len(result["quarantined"]) == 1
    assert result["quarantined"][0]["code"] == "GITHUB_PROVENANCE_MISMATCH"
    assert result["quarantined"][0]["claim"]["issue_number"] == 88


def test_concurrent_status_aggregation_is_deterministic() -> None:
    service = GitHubProvenanceService(resolve_provider=_resolver)
    batches = ((_claim(), _claim(issue_number=88)), (_claim(issue_number=88), _claim()))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(service.aggregate, batches))
    assert results[0] == results[1]


def test_packet_issuance_freezes_only_provider_verified_provenance(
    tmp_path: Path,
) -> None:
    task = PlannerTask(
        task_id="provenance",
        outcome="verify provenance",
        owned_paths=("src/kis_mcp/workflows/coordinator/**",),
        acceptance_checks=("verified",),
    )
    request = PlannerRequest(
        project_id="kis-mcp",
        change_id="217-github-provenance-validation",
        work_id="issue-413",
        slice_id="413",
        revision=1,
        exact_base={"commit_sha": "c" * 40, "tree_sha": "d" * 40},
        tasks=(task,),
        external_provenance=_claim(),
    )
    plan = PlannerService().plan(request)
    service = WorkPacketService(
        state_root=tmp_path,
        project_boundary=tmp_path,
        resolve_runtime=lambda _required: [_runtime_candidate()],
        resolve_provenance=_resolver,
        token_factory=lambda: "assignment-key",
    )
    result = service.issue(
        request=request,
        plan=plan,
        task_id="provenance",
        authority={
            "reservation_id": "res-217",
            "authority_revision": 1,
            "lease_id": "lease-217",
            "fence_token": 1,
        },
    )
    evidence = result["packet"]["external_provenance"]
    assert evidence["status"] == "verified"
    assert evidence["tuple"] == _claim(repository="nielpieterse0/kis-mcp")
    assert evidence["claim_sha256"]

    stale = PlannerRequest(
        project_id="kis-mcp",
        change_id="217-github-provenance-validation",
        work_id="issue-413-stale",
        slice_id="413-stale",
        revision=1,
        exact_base={"commit_sha": "c" * 40, "tree_sha": "d" * 40},
        tasks=(task,),
        external_provenance=_claim(head_sha="e" * 40),
    )
    with pytest.raises(ReservationAdmissionError, match="GITHUB_PROVENANCE_MISMATCH"):
        service.issue(
            request=stale,
            plan=PlannerService().plan(stale),
            task_id="provenance",
            authority={
                "reservation_id": "res-217",
                "authority_revision": 1,
                "lease_id": "lease-217",
                "fence_token": 1,
            },
        )


def test_verified_envelope_is_tamper_evident() -> None:
    evidence = GitHubProvenanceService(resolve_provider=_resolver).verify(_claim())
    tampered = {**evidence, "tuple": {**evidence["tuple"], "issue_number": 88}}

    with pytest.raises(
        ReservationAdmissionError, match="GITHUB_PROVENANCE_EVIDENCE_INVALID"
    ):
        validate_provenance_evidence(tampered)


def test_runtime_validation_rejects_unknown_provenance_keys_like_the_schema() -> None:
    service = GitHubProvenanceService(resolve_provider=_resolver)
    with pytest.raises(ReservationAdmissionError, match="GITHUB_PROVENANCE_INVALID"):
        service.verify(_claim(unexpected="value"))

    evidence = service.verify(_claim())
    with pytest.raises(
        ReservationAdmissionError, match="GITHUB_PROVENANCE_EVIDENCE_INVALID"
    ):
        validate_provenance_evidence({**evidence, "unexpected": "value"})
    with pytest.raises(ReservationAdmissionError, match="GITHUB_PROVENANCE_INVALID"):
        validate_provenance_evidence(
            {**evidence, "tuple": {**evidence["tuple"], "unexpected": "value"}}
        )


def test_delivery_preserves_frozen_head_and_adds_observed_merge_sha() -> None:
    frozen = GitHubProvenanceService(resolve_provider=_resolver).verify(_claim())
    delivered = validate_delivery_provenance(frozen, _claim(merge_sha=MERGE))

    assert delivered["tuple"]["head_sha"] == HEAD
    assert delivered["tuple"]["merge_sha"] == MERGE
    assert delivered["frozen_claim_sha256"] == frozen["claim_sha256"]

    with pytest.raises(
        ReservationAdmissionError, match="GITHUB_PROVENANCE_DELIVERY_MISMATCH"
    ):
        validate_delivery_provenance(frozen, _claim(head_sha="c" * 40, merge_sha=MERGE))


def _runtime_candidate() -> dict[str, object]:
    return {
        "binding_id": "kis-dev-codex",
        "worker_id": "implementer",
        "worker_revision": "develop-code@current",
        "runtime_id": "kis-dev",
        "runtime_revision": "f" * 40,
        "tool_id": "codex-cli",
        "tool_revision": "0.147.0",
        "protocol": "mcp",
        "interface": "reviewable-worker-v1",
        "endpoint": "127.0.0.1:8011/mcp",
        "binding": "development",
        "transport": "mcp",
        "capabilities": [],
        "observed_at": "2026-08-20T12:00:00Z",
        "grants_mutation_authority": False,
    }
