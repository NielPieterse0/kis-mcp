from __future__ import annotations

from dataclasses import replace

import pytest

import kis_mcp.work_management as work_management
from kis_mcp.work_management.contracts import (
    LifecycleState,
    RecordType,
    WorkRecord,
)
from kis_mcp.work_management.reviews import (
    ExtractionMode,
    FindingDetails,
    FindingDisposition,
    FindingRecord,
    FindingState,
    FindingTransitionRejected,
    ObservationDisposition,
    ReviewArtifactKind,
    ReviewBudget,
    ReviewCoverage,
    ReviewObservation,
    ReviewRequest,
    ReviewResult,
    ReviewStatus,
    ReviewTarget,
    ReviewType,
    create_review_evidence_manifest,
    evaluate_finding_transition,
    extract_review_records,
    transition_finding,
)


def revision(character: str = "a") -> str:
    return character * 40


def target(**overrides: object) -> ReviewTarget:
    values: dict[str, object] = {
        "project_id": "kis-mcp",
        "repository": "NielPieterse0/kis-mcp",
        "commit": revision(),
    }
    values.update(overrides)
    return ReviewTarget(**values)  # type: ignore[arg-type]


def review_record(**overrides: object) -> WorkRecord:
    values: dict[str, object] = {
        "record_id": "REV-55",
        "project_id": "kis-mcp",
        "title": "P4 review evidence",
        "record_type": RecordType.REVIEW_RUN,
        "state": LifecycleState.ACTIVE,
    }
    values.update(overrides)
    return WorkRecord(**values)  # type: ignore[arg-type]


def request(**overrides: object) -> ReviewRequest:
    values: dict[str, object] = {
        "record": review_record(),
        "review_id": "REV-55",
        "review_type": ReviewType.CODE,
        "workflow_version": "code-review@1",
        "target": target(),
        "requester": "operator",
        "started_at": "2026-08-07T00:00:00+00:00",
        "status": ReviewStatus.ACTIVE,
        "extraction_mode": ExtractionMode.VALIDATED_FINDINGS,
        "exclusions": ("generated files",),
        "assumptions": ("local diff is authoritative",),
        "unknowns": ("live backend coverage",),
        "budget": ReviewBudget(
            max_evidence_chars=10000,
            max_observations=100,
            max_findings=25,
        ),
    }
    values.update(overrides)
    return ReviewRequest(**values)  # type: ignore[arg-type]


def coverage(**overrides: object) -> ReviewCoverage:
    values: dict[str, object] = {
        "complete": True,
        "reviewed": ("src/kis_mcp/work_management",),
        "gaps": (),
        "truncated": False,
    }
    values.update(overrides)
    return ReviewCoverage(**values)  # type: ignore[arg-type]


def observation(
    observation_id: str,
    disposition: ObservationDisposition,
    *,
    record_type: RecordType | None = None,
    security: bool = False,
) -> ReviewObservation:
    return ReviewObservation(
        observation_id=observation_id,
        review_id="REV-55",
        project_id="kis-mcp",
        disposition=disposition,
        summary=f"Observation {observation_id}",
        evidence=("tests/work_management/test_reviews.py:1",),
        location="src/kis_mcp/work_management/reviews.py:1",
        confidence="high",
        severity="medium",
        record_type=record_type,
        security=security,
    )


def result(*observations: ReviewObservation) -> ReviewResult:
    return ReviewResult(
        request=request(status=ReviewStatus.COMPLETED, completed_at="2026-08-07T00:05:00+00:00"),
        coverage=coverage(),
        observations=observations,
        artifacts=create_review_evidence_manifest("REV-55"),
        diagnostics=(),
    )


def finding_record(
    *,
    state: FindingState = FindingState.CANDIDATE,
    details: FindingDetails | None = None,
    record_type: RecordType = RecordType.FINDING,
) -> FindingRecord:
    record_id = "SEC-55" if record_type is RecordType.SECURITY_FINDING else "FIND-55"
    return FindingRecord(
        record=WorkRecord(
            record_id=record_id,
            project_id="kis-mcp",
            title="Review finding",
            record_type=record_type,
            state=LifecycleState.TRIAGE,
        ),
        details=details
        or FindingDetails(
            source_review_id="REV-55",
            source_observation_id="OBS-1",
            evidence=("src/example.py:10",),
            location="src/example.py:10",
            confidence="high",
            severity="medium",
        ),
        state=state,
    )


def test_review_request_serializes_exact_target_and_context() -> None:
    payload = request().to_json_dict()

    assert payload["review_id"] == "REV-55"
    assert payload["review_type"] == "code"
    assert payload["target"]["commit"] == revision()
    assert payload["extraction_mode"] == "validated_findings"
    assert payload["budget"]["max_findings"] == 25
    assert payload["exclusions"] == ["generated files"]


@pytest.mark.parametrize("review_id", ["FIND-55", "REV-x", "rev-55", ""])
def test_review_request_requires_review_identity(review_id: str) -> None:
    with pytest.raises(ValueError, match="REV"):
        request(review_id=review_id)


def test_review_target_requires_bounded_selector() -> None:
    with pytest.raises(ValueError, match="selector"):
        target(commit=None)


def test_review_target_requires_complete_range() -> None:
    with pytest.raises(ValueError, match="range"):
        target(commit=None, range_start=revision("b"), range_end=None)


def test_review_target_normalizes_unique_relative_paths() -> None:
    value = target(commit=None, paths=("src/b.py", "src/a.py"))

    assert value.paths == ("src/a.py", "src/b.py")
    with pytest.raises(ValueError, match="parent traversal"):
        target(commit=None, paths=("../outside.py",))


def test_review_budget_requires_positive_values() -> None:
    with pytest.raises(ValueError, match="positive"):
        ReviewBudget(max_evidence_chars=0, max_observations=1, max_findings=1)


def test_partial_coverage_preserves_gaps_and_truncation() -> None:
    value = coverage(
        complete=False,
        reviewed=("src",),
        gaps=("tests unavailable",),
        truncated=True,
    )

    assert value.to_json_dict() == {
        "complete": False,
        "reviewed": ["src"],
        "gaps": ["tests unavailable"],
        "truncated": True,
    }


def test_complete_coverage_rejects_gaps_or_truncation() -> None:
    with pytest.raises(ValueError, match="complete coverage"):
        coverage(gaps=("gap",))
    with pytest.raises(ValueError, match="complete coverage"):
        coverage(truncated=True)


def test_review_manifest_uses_canonical_paths_without_persistence(tmp_path) -> None:
    before = tuple(tmp_path.iterdir())
    manifest = create_review_evidence_manifest("REV-55")

    assert tuple(tmp_path.iterdir()) == before
    assert {artifact.kind for artifact in manifest.artifacts} == {
        ReviewArtifactKind.REQUEST,
        ReviewArtifactKind.REPORT,
        ReviewArtifactKind.RESULT,
        ReviewArtifactKind.COVERAGE,
        ReviewArtifactKind.CLOSEOUT,
    }
    assert {artifact.path for artifact in manifest.artifacts} == {
        ".work/reviews/REV-55/request.json",
        ".work/reviews/REV-55/report.md",
        ".work/reviews/REV-55/result.json",
        ".work/reviews/REV-55/coverage.json",
        ".work/reviews/REV-55/closeout.json",
    }


def test_review_manifest_can_include_sarif() -> None:
    manifest = create_review_evidence_manifest("REV-55", include_sarif=True)

    assert ReviewArtifactKind.SARIF in {artifact.kind for artifact in manifest.artifacts}
    assert ".work/reviews/REV-55/report.sarif" in {
        artifact.path for artifact in manifest.artifacts
    }


def test_review_result_preserves_partial_coverage_and_groups_observations() -> None:
    value = ReviewResult(
        request=request(status=ReviewStatus.COMPLETED, completed_at="2026-08-07T00:05:00+00:00"),
        coverage=coverage(complete=False, gaps=("dependency graph",)),
        observations=(
            observation("OBS-1", ObservationDisposition.VALIDATED_FINDING),
            observation("OBS-2", ObservationDisposition.DECISION_REQUIRED),
            observation("OBS-3", ObservationDisposition.ASSUMPTION),
            observation("OBS-4", ObservationDisposition.RISK),
        ),
        artifacts=create_review_evidence_manifest("REV-55"),
        diagnostics=("PARTIAL_COVERAGE",),
    )

    payload = value.to_json_dict()
    assert payload["coverage"]["complete"] is False
    assert payload["findings"] == ["OBS-1"]
    assert payload["decisions"] == ["OBS-2"]
    assert payload["assumptions"] == ["OBS-3"]
    assert payload["risks"] == ["OBS-4"]
    assert payload["diagnostics"] == ["PARTIAL_COVERAGE"]


def test_review_result_rejects_identity_mismatch_and_duplicate_observations() -> None:
    mismatched = replace(
        observation("OBS-1", ObservationDisposition.INFORMATIONAL),
        review_id="REV-99",
    )
    with pytest.raises(ValueError, match="identity"):
        result(mismatched)
    duplicate = observation("OBS-1", ObservationDisposition.INFORMATIONAL)
    with pytest.raises(ValueError, match="unique"):
        result(duplicate, duplicate)


def test_report_only_and_noise_dispositions_do_not_extract_records() -> None:
    value = result(
        observation("OBS-1", ObservationDisposition.REJECTED),
        observation("OBS-2", ObservationDisposition.INFORMATIONAL),
        observation("OBS-3", ObservationDisposition.RECOMMENDATION),
    )

    assert extract_review_records(value, ExtractionMode.REPORT_ONLY) == ()
    assert extract_review_records(value, ExtractionMode.FULL_GOVERNANCE) == ()


def test_validated_findings_extracts_only_finding_records() -> None:
    value = result(
        observation("OBS-1", ObservationDisposition.VALIDATED_FINDING),
        observation(
            "OBS-2",
            ObservationDisposition.VALIDATED_FINDING,
            security=True,
        ),
        observation("OBS-3", ObservationDisposition.RISK),
    )

    extracted = extract_review_records(value, ExtractionMode.VALIDATED_FINDINGS)

    assert [item.record_type for item in extracted] == [
        RecordType.FINDING,
        RecordType.SECURITY_FINDING,
    ]
    assert extracted == extract_review_records(
        value,
        ExtractionMode.VALIDATED_FINDINGS,
    )
    assert extracted[0].deduplication_key == "REV-55:OBS-1:finding"


def test_full_governance_extracts_disposition_compatible_records() -> None:
    value = result(
        observation("OBS-1", ObservationDisposition.VALIDATED_FINDING),
        observation("OBS-2", ObservationDisposition.DECISION_REQUIRED),
        observation("OBS-3", ObservationDisposition.ASSUMPTION),
        observation("OBS-4", ObservationDisposition.RISK),
        observation(
            "OBS-5",
            ObservationDisposition.DEFERRED_CANDIDATE,
            record_type=RecordType.HOLD,
        ),
        observation(
            "OBS-6",
            ObservationDisposition.DEFERRED_CANDIDATE,
            record_type=RecordType.TASK,
        ),
    )

    extracted = extract_review_records(value, ExtractionMode.FULL_GOVERNANCE)

    assert [item.record_type for item in extracted] == [
        RecordType.FINDING,
        RecordType.DECISION,
        RecordType.ASSUMPTION,
        RecordType.RISK,
        RecordType.HOLD,
        RecordType.TASK,
    ]
    assert extracted[-1].state is LifecycleState.DEFERRED
    assert all(item.project_id == "kis-mcp" for item in extracted)
    assert all(item.source_review_id == "REV-55" for item in extracted)


def test_observation_rejects_incompatible_record_type() -> None:
    with pytest.raises(ValueError, match="record_type"):
        observation(
            "OBS-1",
            ObservationDisposition.RISK,
            record_type=RecordType.DECISION,
        )


def test_finding_lifecycle_accepts_declared_path() -> None:
    candidate = finding_record()
    validated = transition_finding(candidate, FindingState.VALIDATED)
    accepted = transition_finding(validated, FindingState.ACCEPTED)
    remediation = transition_finding(
        replace(
            accepted,
            details=replace(accepted.details, remediation_record_id="TASK-55"),
        ),
        FindingState.REMEDIATION,
    )
    verification = transition_finding(
        replace(
            remediation,
            details=replace(remediation.details, fix_pull_request="PR-68"),
        ),
        FindingState.VERIFICATION,
    )
    closed = transition_finding(
        replace(
            verification,
            details=replace(
                verification.details,
                follow_up_verification="verify-55",
            ),
        ),
        FindingState.CLOSED,
    )

    assert closed.state is FindingState.CLOSED
    assert closed.details.remediation_record_id == "TASK-55"
    assert closed.details.fix_pull_request == "PR-68"
    assert closed.details.follow_up_verification == "verify-55"


def test_finding_lifecycle_rejects_invalid_jump_without_mutation() -> None:
    value = finding_record()

    decision = evaluate_finding_transition(value, FindingState.CLOSED)
    assert decision.allowed is False
    assert decision.reasons == ("transition_not_declared",)
    with pytest.raises(FindingTransitionRejected):
        transition_finding(value, FindingState.CLOSED)
    assert value.state is FindingState.CANDIDATE


def test_finding_state_prerequisites_are_enforced() -> None:
    value = finding_record()
    assert evaluate_finding_transition(value, FindingState.VALIDATED).allowed is True

    accepted = transition_finding(
        transition_finding(value, FindingState.VALIDATED),
        FindingState.ACCEPTED,
    )
    assert evaluate_finding_transition(accepted, FindingState.REMEDIATION).reasons == (
        "remediation_record_required",
    )

    remediation = finding_record(
        state=FindingState.REMEDIATION,
        details=replace(
            value.details,
            validation_disposition=FindingDisposition.ACCEPTED,
            remediation_record_id="TASK-55",
        ),
    )
    assert evaluate_finding_transition(remediation, FindingState.VERIFICATION).reasons == (
        "fix_pull_request_required",
    )


def test_finding_record_supports_security_finding_prefix() -> None:
    value = finding_record(record_type=RecordType.SECURITY_FINDING)

    assert value.record.record_id == "SEC-55"
    assert value.to_json_dict()["record"]["record_type"] == "security_finding"


def test_work_management_package_exports_p4_review_contracts() -> None:
    expected = {
        "ExtractionMode",
        "ExtractedReviewRecord",
        "FindingDetails",
        "FindingDisposition",
        "FindingRecord",
        "FindingState",
        "FindingTransitionDecision",
        "FindingTransitionRejected",
        "ObservationDisposition",
        "ReviewArtifact",
        "ReviewArtifactKind",
        "ReviewBudget",
        "ReviewCoverage",
        "ReviewEvidenceManifest",
        "ReviewObservation",
        "ReviewRequest",
        "ReviewResult",
        "ReviewStatus",
        "ReviewTarget",
        "ReviewType",
        "create_review_evidence_manifest",
        "evaluate_finding_transition",
        "extract_review_records",
        "transition_finding",
    }

    assert expected.issubset(set(work_management.__all__))
    assert all(hasattr(work_management, name) for name in expected)


def test_review_request_requires_matching_typed_work_record() -> None:
    value = request()

    assert value.record.record_type is RecordType.REVIEW_RUN
    assert value.record.record_id == value.review_id
    assert value.record.project_id == value.target.project_id
    assert value.to_json_dict()["record"]["record_type"] == "review_run"

    with pytest.raises(ValueError, match="record identity"):
        request(record=review_record(record_id="REV-56"))
    with pytest.raises(ValueError, match="record type"):
        request(
            record=WorkRecord(
                record_id="TASK-55",
                project_id="kis-mcp",
                title="Wrong type",
                record_type=RecordType.TASK,
            )
        )


def test_operator_selected_recommendation_can_extract_as_task() -> None:
    selected = observation(
        "OBS-7",
        ObservationDisposition.RECOMMENDATION,
        record_type=RecordType.TASK,
    )
    value = result(selected)

    assert extract_review_records(value, ExtractionMode.VALIDATED_FINDINGS) == ()
    extracted = extract_review_records(value, ExtractionMode.FULL_GOVERNANCE)
    assert len(extracted) == 1
    assert extracted[0].record_type is RecordType.TASK
    assert extracted[0].state is LifecycleState.TRIAGE


def test_failed_review_result_retains_partial_evidence_without_extraction() -> None:
    value = ReviewResult(
        request=request(
            status=ReviewStatus.FAILED,
            completed_at="2026-08-07T00:05:00+00:00",
        ),
        coverage=coverage(complete=False, gaps=("backend failed",)),
        observations=(
            observation("OBS-1", ObservationDisposition.VALIDATED_FINDING),
        ),
        artifacts=create_review_evidence_manifest("REV-55"),
        diagnostics=("AGENT_BACKEND_FAILED",),
    )

    assert value.to_json_dict()["status"] == "failed"
    assert value.to_json_dict()["coverage"]["complete"] is False
    assert extract_review_records(value, ExtractionMode.FULL_GOVERNANCE) == ()


def test_review_result_enforces_findings_budget() -> None:
    limited = request(
        status=ReviewStatus.COMPLETED,
        completed_at="2026-08-07T00:05:00+00:00",
        budget=ReviewBudget(
            max_evidence_chars=1000,
            max_observations=10,
            max_findings=1,
        ),
    )

    with pytest.raises(ValueError, match="findings exceed"):
        ReviewResult(
            request=limited,
            coverage=coverage(),
            observations=(
                observation("OBS-2", ObservationDisposition.VALIDATED_FINDING),
                observation("OBS-1", ObservationDisposition.VALIDATED_FINDING),
            ),
            artifacts=create_review_evidence_manifest("REV-55"),
        )


def test_review_result_orders_observations_deterministically() -> None:
    first = ReviewResult(
        request=request(
            status=ReviewStatus.COMPLETED,
            completed_at="2026-08-07T00:05:00+00:00",
        ),
        coverage=coverage(),
        observations=(
            observation("OBS-2", ObservationDisposition.INFORMATIONAL),
            observation("OBS-1", ObservationDisposition.INFORMATIONAL),
        ),
        artifacts=create_review_evidence_manifest("REV-55"),
    )
    second = replace(first, observations=tuple(reversed(first.observations)))

    assert [item.observation_id for item in first.observations] == ["OBS-1", "OBS-2"]
    assert first.to_json_dict() == second.to_json_dict()


def test_extracted_record_preserves_source_location() -> None:
    extracted = extract_review_records(
        result(observation("OBS-8", ObservationDisposition.VALIDATED_FINDING)),
        ExtractionMode.VALIDATED_FINDINGS,
    )

    assert extracted[0].location == "src/kis_mcp/work_management/reviews.py:1"
    assert extracted[0].to_json_dict()["location"] == extracted[0].location


def test_review_result_enforces_evidence_character_budget() -> None:
    constrained = request(
        status=ReviewStatus.COMPLETED,
        completed_at="2026-08-07T00:05:00+00:00",
        budget=ReviewBudget(
            max_evidence_chars=5,
            max_observations=10,
            max_findings=10,
        ),
    )

    with pytest.raises(ValueError, match="evidence exceeds"):
        ReviewResult(
            request=constrained,
            coverage=coverage(),
            observations=(
                observation("OBS-1", ObservationDisposition.INFORMATIONAL),
            ),
            artifacts=create_review_evidence_manifest("REV-55"),
        )


def test_review_request_rejects_completion_before_start() -> None:
    with pytest.raises(ValueError, match="before started_at"):
        request(
            status=ReviewStatus.COMPLETED,
            completed_at="2026-08-06T23:59:00+00:00",
        )


def test_failed_review_requires_diagnostics() -> None:
    with pytest.raises(ValueError, match="diagnostics"):
        ReviewResult(
            request=request(
                status=ReviewStatus.FAILED,
                completed_at="2026-08-07T00:05:00+00:00",
            ),
            coverage=coverage(complete=False, gaps=("backend failed",)),
            observations=(),
            artifacts=create_review_evidence_manifest("REV-55"),
        )


def test_finding_disposition_is_structured_and_state_consistent() -> None:
    candidate = finding_record()
    validated = transition_finding(candidate, FindingState.VALIDATED)
    accepted = transition_finding(validated, FindingState.ACCEPTED)

    assert validated.details.validation_disposition is FindingDisposition.VALIDATED
    assert accepted.details.validation_disposition is FindingDisposition.ACCEPTED

    with pytest.raises(ValueError, match="disposition"):
        finding_record(
            state=FindingState.ACCEPTED,
            details=replace(
                candidate.details,
                validation_disposition=FindingDisposition.REJECTED,
            ),
        )


def test_review_request_rejects_mixed_timestamp_awareness() -> None:
    with pytest.raises(ValueError, match="timezone awareness"):
        request(
            started_at="2026-08-07T00:00:00",
            status=ReviewStatus.COMPLETED,
            completed_at="2026-08-07T00:05:00+00:00",
        )


def test_finding_transition_decision_serializes_json_safely() -> None:
    decision = evaluate_finding_transition(finding_record(), FindingState.CLOSED)

    assert decision.to_json_dict() == {
        "allowed": False,
        "reasons": ["transition_not_declared"],
    }


def test_review_manifest_preserves_canonical_artifact_order() -> None:
    without_sarif = create_review_evidence_manifest("REV-55")
    with_sarif = create_review_evidence_manifest("REV-55", include_sarif=True)

    assert [artifact.kind for artifact in without_sarif.artifacts] == [
        ReviewArtifactKind.REQUEST,
        ReviewArtifactKind.REPORT,
        ReviewArtifactKind.RESULT,
        ReviewArtifactKind.COVERAGE,
        ReviewArtifactKind.CLOSEOUT,
    ]
    assert [artifact.kind for artifact in with_sarif.artifacts] == [
        ReviewArtifactKind.REQUEST,
        ReviewArtifactKind.REPORT,
        ReviewArtifactKind.RESULT,
        ReviewArtifactKind.COVERAGE,
        ReviewArtifactKind.SARIF,
        ReviewArtifactKind.CLOSEOUT,
    ]
