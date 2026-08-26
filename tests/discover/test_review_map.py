from __future__ import annotations

import pytest

from kis_mcp.discover.change_inspection_contracts import (
    ChangedFile,
    ChangeIdentity,
    ChangeImpactSummary,
    InspectChangeResponse,
)
from kis_mcp.discover.review_map import build_review_map
from kis_mcp.discover.review_map_contracts import ReviewMapLimits


def _file(path: str, category: str) -> ChangedFile:
    return ChangedFile(
        path=path,
        previous_path=None,
        staged_status=None,
        worktree_status="modified",
        untracked=False,
        categories=(category,),
    )


def _inspection(
    *files: ChangedFile, fingerprint: str = "a" * 64
) -> InspectChangeResponse:
    return InspectChangeResponse(
        available=True,
        project_path=r"C:\Projects\fixture",
        repository_root=r"C:\Projects\fixture",
        change=ChangeIdentity(source="working_tree", fingerprint=fingerprint),
        changed_files=files,
        affected_scopes=("src", "tests"),
        changed_tests=tuple(item.path for item in files if "test" in item.categories),
        contract_paths=(),
        documentation_paths=(),
        configuration_paths=(),
        policy_paths=(),
        impact_summary=ChangeImpactSummary(
            total_files=len(files),
            source_files=sum("source" in item.categories for item in files),
            test_files=sum("test" in item.categories for item in files),
            contract_files=0,
            documentation_files=0,
            configuration_files=0,
            policy_files=0,
            other_files=0,
        ),
        diagnostics=(),
        unknowns=(),
        confidence="high",
        truncated=False,
    )


def test_review_map_is_source_bound_and_deterministic() -> None:
    inspection = _inspection(
        _file("tests/test_beta.py", "test"),
        _file("src/pkg/beta.py", "source"),
        _file("src/pkg/alpha.py", "source"),
    )
    limits = ReviewMapLimits(max_files=20, max_sections=20, max_relationships=20)

    first = build_review_map(inspection, limits=limits)
    second = build_review_map(inspection, limits=limits)

    assert first == second
    assert first["source_fingerprint"] == "a" * 64
    assert first["included_files"] == [
        "src/pkg/alpha.py",
        "src/pkg/beta.py",
        "tests/test_beta.py",
    ]
    assert first["gate_authority"] == {
        "review": False,
        "verification": False,
        "merge_readiness": False,
        "mutation": False,
    }
    assert all(section["review_status"] == "pending" for section in first["sections"])


def test_review_map_rejects_stale_source_fingerprint() -> None:
    inspection = _inspection(_file("src/pkg/alpha.py", "source"))
    with pytest.raises(ValueError, match="source fingerprint is stale"):
        build_review_map(
            inspection,
            limits=ReviewMapLimits(),
            expected_source_fingerprint="b" * 64,
        )


def test_review_map_bounds_and_explicit_omissions() -> None:
    inspection = _inspection(
        _file("src/a.py", "source"),
        _file("src/b.py", "source"),
        _file("tests/test_a.py", "test"),
    )
    result = build_review_map(
        inspection,
        limits=ReviewMapLimits(max_files=2, max_sections=1, max_relationships=1),
    )

    assert result["truncated"] is True
    assert result["incomplete"] is True
    assert result["omitted_files"]
    assert len(result["sections"]) == 1
    assert len(result["relationships"]) <= 1


def test_review_map_reports_relationship_truncation() -> None:
    inspection = _inspection(
        _file("src/a.py", "source"),
        _file("tests/test_a.py", "test"),
    )
    result = build_review_map(
        inspection,
        limits=ReviewMapLimits(max_files=10, max_sections=10, max_relationships=1),
    )

    assert result["omitted_relationship_count"] == 1
    assert result["truncated"] is True
    assert result["incomplete"] is True
