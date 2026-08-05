from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.discover.context_contracts import (
    MIN_CONTEXT_CHARS,
    CodeContextBudget,
    ContextFile,
    ContextModule,
    ContextOmissions,
    ContextProvenance,
    ContextRelationship,
    ContextSymbol,
    ContextUnknown,
    GetCodeContextRequest,
    GetCodeContextResponse,
)
from kis_mcp.discover.contracts import Confidence, ProjectIdentity


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts" / "discover"


def _schema(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def _budget(**overrides: int) -> CodeContextBudget:
    values = {
        "max_chars": 8_000,
        "max_files": 4,
        "max_symbols": 8,
        "max_relationships": 12,
    }
    values.update(overrides)
    return CodeContextBudget(**values)


def test_request_requires_project_task_and_explicit_positive_budget() -> None:
    request = GetCodeContextRequest(
        project=r"C:\Projects\example",
        task="Add GitLab merge request evidence",
        budget=_budget(),
    )

    assert request.project == r"C:\Projects\example"
    assert request.task == "Add GitLab merge request evidence"
    assert request.to_json_dict()["budget"]["max_files"] == 4

    with pytest.raises(ValueError, match="project"):
        GetCodeContextRequest(project=" ", task="task", budget=_budget())
    with pytest.raises(ValueError, match="task"):
        GetCodeContextRequest(
            project=r"C:\Projects\example",
            task=" ",
            budget=_budget(),
        )
    with pytest.raises(ValueError, match="minimum"):
        _budget(max_chars=MIN_CONTEXT_CHARS - 1)
    with pytest.raises(ValueError, match="positive"):
        _budget(max_files=0)


def test_response_serializes_stable_versioned_contract() -> None:
    provenance = ContextProvenance(
        kind="observed",
        provider="local_filesystem",
        identifier="src/service.py",
    )
    project = ProjectIdentity(
        project_id="local:123",
        canonical_path=r"C:\Projects\example",
        repository_root=r"C:\Projects\example",
        git_root=r"C:\Projects\example",
        remote_identity=None,
    )
    response = GetCodeContextResponse(
        project=project,
        task="repair service",
        budget=_budget(),
        task_terms=("repair", "service"),
        files=(
            ContextFile(
                path="src/service.py",
                category="source",
                relevance_score=120,
                matched_terms=("service",),
                excerpt="def repair_service():\n    pass\n",
                start_line=1,
                end_line=2,
                truncated=False,
                provenance=provenance,
            ),
        ),
        modules=(
            ContextModule(
                name="service",
                path="src/service.py",
                relevance_score=100,
                matched_terms=("service",),
                provenance=ContextProvenance(
                    kind="parser_confirmed",
                    provider="python_ast",
                    identifier="service",
                ),
            ),
        ),
        symbols=(
            ContextSymbol(
                qualified_name="service.repair_service",
                module="service",
                name="repair_service",
                kind="function",
                path="src/service.py",
                line=1,
                end_line=2,
                relevance_score=140,
                matched_terms=("repair", "service"),
                provenance=ContextProvenance(
                    kind="parser_confirmed",
                    provider="python_ast",
                    identifier="service.repair_service",
                ),
            ),
        ),
        relationships=(
            ContextRelationship(
                kind="call",
                source="service.repair_service",
                target="helper",
                path="src/service.py",
                line=1,
                relevance_score=80,
                confidence="high",
                provenance=ContextProvenance(
                    kind="parser_confirmed",
                    provider="python_ast",
                    identifier="service.repair_service:1:helper",
                ),
            ),
        ),
        instructions=("AGENTS.md",),
        tests=("tests/test_service.py",),
        contracts=(),
        git={"available": True, "branch": "main", "head": "a" * 40},
        providers={
            "filesystem": {"available": True, "provider": "local_filesystem"},
            "semantic": {"available": True, "provider": "python_ast"},
        },
        unknowns=(
            ContextUnknown(
                code="REMOTE_CONTEXT_UNAVAILABLE",
                reason="Remote evidence is not configured.",
            ),
        ),
        omissions=ContextOmissions(
            files=2,
            symbols=3,
            relationships=4,
            unreadable_files=0,
        ),
        confidence=Confidence.MEDIUM,
        truncated=True,
        truncation_reasons=("max_files",),
        fingerprint="a" * 64,
    )

    payload = response.to_json_dict()

    assert payload["schema_version"] == 1
    assert payload["tool"] == "get_code_context"
    assert payload["project"]["project_id"] == "local:123"
    assert payload["files"][0]["path"] == "src/service.py"
    assert payload["relationships"][0]["kind"] == "call"
    assert payload["omissions"] == {
        "files": 2,
        "symbols": 3,
        "relationships": 4,
        "unreadable_files": 0,
    }
    assert payload["confidence"] == "medium"


def test_response_rejects_invalid_fingerprint_and_references() -> None:
    project = ProjectIdentity(
        project_id="local:123",
        canonical_path=r"C:\Projects\example",
        repository_root=r"C:\Projects\example",
        git_root=None,
        remote_identity=None,
    )

    with pytest.raises(ValueError, match="fingerprint"):
        GetCodeContextResponse(
            project=project,
            task="task",
            budget=_budget(),
            task_terms=("task",),
            files=(),
            modules=(),
            symbols=(),
            relationships=(),
            instructions=(),
            tests=(),
            contracts=(),
            git={"available": False},
            providers={},
            unknowns=(),
            omissions=ContextOmissions(0, 0, 0, 0),
            confidence=Confidence.LOW,
            truncated=False,
            truncation_reasons=(),
            fingerprint="bad",
        )


def test_request_and_response_schemas_are_strict() -> None:
    request_validator = Draft202012Validator(
        _schema("get-code-context-request.schema.json")
    )
    response_validator = Draft202012Validator(
        _schema("get-code-context-response.schema.json")
    )
    request = GetCodeContextRequest(
        project=r"C:\Projects\example",
        task="repair service",
        budget=_budget(),
    )
    project = ProjectIdentity(
        project_id="local:123",
        canonical_path=r"C:\Projects\example",
        repository_root=r"C:\Projects\example",
        git_root=None,
        remote_identity=None,
    )
    response = GetCodeContextResponse(
        project=project,
        task=request.task,
        budget=request.budget,
        task_terms=("repair", "service"),
        files=(),
        modules=(),
        symbols=(),
        relationships=(),
        instructions=(),
        tests=(),
        contracts=(),
        git={"available": False, "status": "unavailable"},
        providers={
            "filesystem": {"available": True, "provider": "local_filesystem"}
        },
        unknowns=(
            ContextUnknown(
                code="NO_RELEVANT_FILES",
                reason="No relevant files were retained.",
            ),
        ),
        omissions=ContextOmissions(0, 0, 0, 0),
        confidence=Confidence.LOW,
        truncated=False,
        truncation_reasons=(),
        fingerprint="b" * 64,
    )

    assert list(request_validator.iter_errors(request.to_json_dict())) == []
    assert list(response_validator.iter_errors(response.to_json_dict())) == []
    assert list(
        request_validator.iter_errors(
            {
                **request.to_json_dict(),
                "unexpected": True,
            }
        )
    )
    assert list(
        response_validator.iter_errors(
            {
                **response.to_json_dict(),
                "unexpected": True,
            }
        )
    )
