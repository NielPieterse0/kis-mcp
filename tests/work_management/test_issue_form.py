from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FORM_PATH = REPOSITORY_ROOT / ".github" / "ISSUE_TEMPLATE" / "work-item.yml"


def test_standard_work_item_form_keeps_title_plain_and_body_bounded() -> None:
    content = FORM_PATH.read_text(encoding="utf-8")

    assert 'title: ""' in content
    assert "plain bounded outcome" in content
    assert "status, priority, record IDs, or type prefixes" in content
    assert "label: Outcome" in content
    assert "label: Context" in content
    assert "label: Acceptance criteria" in content
    assert "label: Constraints / dependencies" in content
    assert "label: Evidence / references" in content
    assert content.count("required: true") == 2


def test_standard_work_item_form_does_not_duplicate_project_metadata() -> None:
    content = FORM_PATH.read_text(encoding="utf-8")
    for label in (
        "Priority",
        "Complexity",
        "Risk Triggers",
        "Status",
        "Execution Owner",
    ):
        assert f"label: {label}" not in content
