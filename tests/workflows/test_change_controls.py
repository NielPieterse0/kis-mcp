from __future__ import annotations

import pytest

from kis_mcp.workflows.change_controls import select_change_controls


def test_small_change_uses_compact_execution_defaults() -> None:
    result = select_change_controls(complexity="small")
    assert result.max_verifications == 6
    assert result.review_types == ()


def test_medium_and_large_defaults() -> None:
    medium = select_change_controls(complexity="medium")
    large = select_change_controls(complexity="large")
    assert medium.max_verifications == 20
    assert large.max_verifications == 20
    assert medium.review_types == ("code-quality",)
    assert large.review_types == ("code-quality",)


def test_explicit_review_adds_to_base_review() -> None:
    result = select_change_controls(
        complexity="medium",
        review_types=("test-quality",),
    )
    assert result.review_types == ("code-quality", "test-quality")


def test_invalid_complexity_is_rejected() -> None:
    with pytest.raises(ValueError, match="complexity"):
        select_change_controls(complexity="heroic")
