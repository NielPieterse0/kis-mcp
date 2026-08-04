from __future__ import annotations

import importlib
import json
from dataclasses import FrozenInstanceError

import pytest


def _contracts():
    return importlib.import_module("kis_mcp.discover.contracts")


def test_discover_contract_vocabulary_is_stable() -> None:
    contracts = _contracts()

    assert [item.value for item in contracts.Confidence] == ["high", "medium", "low"]
    assert [item.value for item in contracts.TrustState] == [
        "trusted",
        "untrusted",
        "partial",
        "unknown",
    ]
    assert [item.value for item in contracts.Freshness] == [
        "current",
        "stale",
        "unknown",
    ]
    assert [item.value for item in contracts.ProvenanceKind] == [
        "declared",
        "observed",
        "conventional",
        "inferred",
        "remote_observed",
        "governance_required",
        "recommended",
    ]


def test_evidence_contract_is_immutable_and_json_compatible() -> None:
    contracts = _contracts()
    source = contracts.EvidenceSource(
        kind="file",
        provider="local_filesystem",
        identifier="pyproject.toml",
        revision=None,
    )
    provenance = contracts.Provenance(
        kind=contracts.ProvenanceKind.DECLARED,
        source_id="pyproject.toml",
    )
    evidence = contracts.EvidenceItem(
        id="ev-manifest-pyproject",
        kind="manifest",
        subject="project:example",
        source=source,
        provenance=provenance,
        location={"path": "pyproject.toml"},
        trust=contracts.TrustState.TRUSTED,
        confidence=contracts.Confidence.HIGH,
        freshness=contracts.Freshness.CURRENT,
        summary="Python project manifest is present.",
        details={"format": "toml"},
        truncated=False,
    )

    payload = evidence.to_json_dict()

    assert payload == {
        "id": "ev-manifest-pyproject",
        "kind": "manifest",
        "subject": "project:example",
        "source": {
            "kind": "file",
            "provider": "local_filesystem",
            "identifier": "pyproject.toml",
            "revision": None,
        },
        "provenance": {"kind": "declared", "source_id": "pyproject.toml"},
        "location": {"path": "pyproject.toml"},
        "trust": "trusted",
        "confidence": "high",
        "freshness": "current",
        "summary": "Python project manifest is present.",
        "details": {"format": "toml"},
        "truncated": False,
    }
    assert json.loads(json.dumps(payload)) == payload
    with pytest.raises(FrozenInstanceError):
        evidence.summary = "changed"  # type: ignore[misc]


def test_inspect_project_response_has_exact_versioned_envelope() -> None:
    contracts = _contracts()
    response = contracts.InspectProjectResponse(
        project=contracts.ProjectIdentity(
            project_id="local:example",
            canonical_path=r"C:\Projects\example",
            repository_root=r"C:\Projects\example",
            git_root=r"C:\Projects\example",
            remote_identity="github.com/example/example",
        ),
        repository_atlas={"topology": {"files": 1, "directories": 1}},
        code_atlas={},
        verification={},
        contracts={},
        instructions=(),
        git=contracts.GitSummary(
            available=True,
            repository=True,
            branch="main",
            detached=False,
            head="0123456789abcdef",
            status="clean",
            tracked_files=1,
            remote="https://github.com/example/example.git",
            diagnostics=(),
            truncated=False,
        ),
        remote={},
        providers={},
        evidence=(),
        findings=(),
        recommendations=(),
        handoffs=(),
        assumptions=(),
        unknowns=(),
        confidence=contracts.Confidence.HIGH,
        truncated=False,
        truncation_reasons=(),
    )

    payload = response.to_json_dict()

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
    assert payload["schema_version"] == 1
    assert payload["tool"] == "inspect_project"
    assert payload["confidence"] == "high"
    assert json.loads(json.dumps(payload)) == payload


def test_structural_error_is_corrective_and_not_a_work_policy_decision() -> None:
    errors = importlib.import_module("kis_mcp.discover.errors")

    error = errors.DiscoverError(
        code="DISCOVER_PATH_OUTSIDE_ROOT",
        message="The project path is outside the configured read boundary.",
        reason="Canonical path is not beneath C:\\Projects.",
        field="path",
        accepted="An existing directory beneath C:\\Projects",
        corrective_actions=("Select a project beneath C:\\Projects.",),
        retryable=False,
    )

    payload = error.to_json_dict()

    assert payload["code"].startswith("DISCOVER_")
    assert not payload["code"].startswith("HR-")
    assert payload["field"] == "path"
    assert payload["corrective_actions"] == [
        "Select a project beneath C:\\Projects."
    ]
    assert json.loads(json.dumps(payload)) == payload


def test_all_planned_d0_d1_record_types_are_immutable_and_serializable() -> None:
    contracts = _contracts()
    records = (
        contracts.EvidenceBudget(
            max_files=100,
            max_directories=25,
            max_total_bytes=1_000_000,
            max_evidence=50,
            max_output_chars=100_000,
            max_depth=8,
        ),
        contracts.TruncationState(
            truncated=True,
            reasons=("max_files",),
            counters={"files": 100},
        ),
        contracts.ProjectTopology(
            files=("pyproject.toml", "src/example.py"),
            directories=("src",),
            excluded_paths=(".git",),
            file_count=2,
            directory_count=1,
        ),
        contracts.ManifestEvidence(
            path="pyproject.toml",
            kind="python_project",
            ecosystem="python",
            package_manager="uv",
            workspace=False,
            confidence=contracts.Confidence.HIGH,
            evidence_ids=("ev-manifest",),
        ),
        contracts.VerificationDeclaration(
            id="verify-python-tests",
            category="test",
            title="Run Python tests",
            authority="discovered_only",
            execution_available=False,
            source_path="pyproject.toml",
            profile="python",
            arguments=("-m", "pytest", "-q"),
            provenance=contracts.ProvenanceKind.DECLARED,
            confidence=contracts.Confidence.HIGH,
            evidence_ids=("ev-pytest",),
        ),
        contracts.ProjectDiagnostic(
            code="MANIFEST_PARSE_FAILED",
            message="A manifest could not be parsed.",
            severity=contracts.Severity.WARNING,
            path="package.json",
        ),
        contracts.Finding(
            id="finding-missing-tests",
            code="TEST_SURFACE_MISSING",
            title="No related tests were found",
            severity=contracts.Severity.WARNING,
            scope="src/example.py",
            observation="The source module has no conventionally related test file.",
            impact="Changes may lack direct regression coverage.",
            evidence_ids=("ev-source",),
            confidence=contracts.Confidence.MEDIUM,
            remediation="Inspect the test strategy before changing this module.",
            owning_plane="discover",
        ),
        contracts.Recommendation(
            id="recommend-add-tests",
            category="verification",
            action="Review whether a focused regression test is required.",
            rationale="No related test evidence was found.",
            evidence_ids=("ev-source",),
            expected_benefit="Improved regression confidence.",
            cost_class="small",
            risks=("Absence of evidence is not proof of absence.",),
            owning_plane="work",
        ),
        contracts.Unknown(
            id="unknown-remote",
            code="REMOTE_EVIDENCE_UNAVAILABLE",
            reason="No approved remote provider was supplied.",
            evidence_ids=(),
        ),
        contracts.Handoff(
            handoff_id="handoff-verify",
            target_plane="work",
            workflow="run_verification",
            reason="Repository verification was discovered but not executed.",
            inputs={"verification_id": "verify-python-tests"},
            evidence_ids=("ev-pytest",),
            required_authority=("verification.execution",),
            expected_result_contract="verification-result-v1",
        ),
        contracts.InspectProjectRequest(
            path=r"C:\Projects\example",
            limits={"max_files": 100},
        ),
    )

    payloads = [record.to_json_dict() for record in records]

    assert json.loads(json.dumps(payloads)) == payloads
    assert payloads[-1] == {
        "path": r"C:\Projects\example",
        "limits": {"max_files": 100},
    }
