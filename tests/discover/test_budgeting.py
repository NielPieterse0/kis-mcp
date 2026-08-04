from __future__ import annotations

import json

import pytest

from kis_mcp.discover.contracts import (
    Confidence,
    EvidenceItem,
    EvidenceSource,
    Finding,
    Freshness,
    GitSummary,
    Handoff,
    InspectProjectResponse,
    ProjectIdentity,
    Provenance,
    ProvenanceKind,
    Recommendation,
    Severity,
    TrustState,
    Unknown,
)
from kis_mcp.discover.errors import DiscoverError


def _evidence(index: int) -> EvidenceItem:
    return EvidenceItem(
        id=f"ev-{index}",
        kind="file",
        subject="local:example",
        source=EvidenceSource(
            kind="file",
            provider="local_filesystem",
            identifier=f"file-{index}.py",
        ),
        provenance=Provenance(
            kind=ProvenanceKind.OBSERVED,
            source_id=f"file-{index}.py",
        ),
        location={"path": f"file-{index}.py"},
        trust=TrustState.TRUSTED,
        confidence=Confidence.HIGH,
        freshness=Freshness.CURRENT,
        summary=f"Evidence {index}",
        details={"index": index},
    )


def _response(*, evidence_count: int = 3, large: bool = False) -> InspectProjectResponse:
    evidence = tuple(_evidence(index) for index in range(evidence_count))
    finding = Finding(
        id="finding-1",
        code="EXAMPLE_FINDING",
        title="Example finding",
        severity=Severity.WARNING,
        scope="file-0.py",
        observation="A material observation was recorded.",
        impact="The repository may need review.",
        evidence_ids=("ev-0",),
        confidence=Confidence.HIGH,
        remediation="Review the affected file.",
        owning_plane="discover",
    )
    recommendation = Recommendation(
        id="recommendation-1",
        category="verification",
        action="Run focused verification.",
        rationale="The finding requires confirmation.",
        evidence_ids=("ev-0",),
        expected_benefit="Higher confidence.",
        cost_class="small",
        risks=(),
        owning_plane="work",
    )
    handoff = Handoff(
        handoff_id="handoff-1",
        target_plane="work",
        workflow="run_verification",
        reason="A verification declaration was discovered.",
        inputs={"verification_id": "verify-tests"},
        evidence_ids=("ev-0",),
        required_authority=("verification.execution",),
        expected_result_contract="verification-result-v1",
    )
    symbols = [
        {
            "qualified_name": f"pkg.module.symbol_{index}",
            "path": "src/pkg/module.py",
            "line": index + 1,
            "documentation": "x" * 200,
        }
        for index in range(100 if large else 2)
    ]
    return InspectProjectResponse(
        project=ProjectIdentity(
            project_id="local:example",
            canonical_path=r"C:\Projects\example",
            repository_root=r"C:\Projects\example",
            git_root=r"C:\Projects\example",
            remote_identity=None,
        ),
        repository_atlas={
            "topology": {
                "files": [f"file-{index}.py" for index in range(100 if large else 3)],
                "directories": ["src", "tests"],
                "file_count": 100 if large else 3,
                "directory_count": 2,
            }
        },
        code_atlas={"symbols": symbols, "summary": {"symbols": len(symbols)}},
        verification={"declarations": [{"id": "verify-tests"}]},
        contracts={},
        instructions=(),
        git=GitSummary(
            available=False,
            repository=False,
            branch=None,
            detached=False,
            head=None,
            status="unavailable",
            tracked_files=0,
            remote=None,
        ),
        remote={"status": "not_configured"},
        providers={"semantic": "not_configured"},
        evidence=evidence,
        findings=(finding,),
        recommendations=(recommendation,),
        handoffs=(handoff,),
        assumptions=({"code": "LOCAL_ONLY"},),
        unknowns=(
            Unknown(
                id="unknown-remote",
                code="REMOTE_EVIDENCE_UNAVAILABLE",
                reason="No remote provider was configured.",
            ),
        ),
        confidence=Confidence.HIGH,
        truncated=False,
        truncation_reasons=(),
    )


def test_exact_evidence_capacity_is_not_truncation() -> None:
    from kis_mcp.discover.budgeting import ResultBudgeter

    response = _response(evidence_count=3)

    bounded = ResultBudgeter(max_evidence=3, max_output_chars=100_000).apply(response)

    assert len(bounded.evidence) == 3
    assert bounded.truncated is False
    assert bounded.truncation_reasons == ()


def test_first_evidence_over_capacity_sets_truncation_and_keeps_references() -> None:
    from kis_mcp.discover.budgeting import ResultBudgeter

    bounded = ResultBudgeter(max_evidence=2, max_output_chars=100_000).apply(
        _response(evidence_count=3)
    )

    assert [item.id for item in bounded.evidence] == ["ev-0", "ev-1"]
    assert bounded.truncated is True
    assert bounded.truncation_reasons == ("max_evidence",)
    assert bounded.findings[0].evidence_ids == ("ev-0",)


def test_dangling_evidence_reference_is_rejected() -> None:
    from dataclasses import replace

    from kis_mcp.discover.budgeting import ResultBudgeter

    response = _response()
    broken = replace(
        response,
        findings=(replace(response.findings[0], evidence_ids=("missing",)),),
    )

    with pytest.raises(DiscoverError) as captured:
        ResultBudgeter(max_evidence=10, max_output_chars=100_000).apply(broken)

    assert captured.value.code == "DISCOVER_EVIDENCE_REFERENCE_INVALID"


def test_output_compaction_preserves_material_envelope_and_references() -> None:
    from kis_mcp.discover.budgeting import ResultBudgeter

    bounded = ResultBudgeter(max_evidence=10, max_output_chars=6_000).apply(
        _response(evidence_count=5, large=True)
    )
    payload = bounded.to_json_dict()
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    assert len(encoded) <= 6_000
    assert set(payload) == {
        "schema_version",
        "tool",
        "project",
        "repository_atlas",
        "code_atlas",
        "verification",
        "contracts",
        "instructions",
        "git",
        "remote",
        "providers",
        "evidence",
        "findings",
        "recommendations",
        "handoffs",
        "assumptions",
        "unknowns",
        "confidence",
        "truncated",
        "truncation_reasons",
    }
    assert payload["findings"][0]["evidence_ids"] == ["ev-0"]
    assert any(item["id"] == "ev-0" for item in payload["evidence"])
    assert payload["unknowns"]
    assert payload["confidence"] == "high"
    assert bounded.truncated is True
    assert "max_output_chars" in bounded.truncation_reasons


def test_minimum_contract_overflow_returns_structural_error() -> None:
    from kis_mcp.discover.budgeting import ResultBudgeter

    with pytest.raises(DiscoverError) as captured:
        ResultBudgeter(max_evidence=1, max_output_chars=100).apply(_response())

    assert captured.value.code == "DISCOVER_OUTPUT_BUDGET_TOO_SMALL"
