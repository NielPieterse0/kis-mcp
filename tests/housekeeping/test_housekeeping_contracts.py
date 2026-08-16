from pathlib import Path

import pytest

from kis_mcp.housekeeping.contracts import (
    HousekeepingTrigger,
    RunMode,
    RunnerKind,
    TriggerKind,
)
from kis_mcp.housekeeping.local_evidence import governed_work_links


def test_apply_trigger_requires_idempotency_key() -> None:
    with pytest.raises(ValueError, match="idempotency_key"):
        HousekeepingTrigger(
            runner=RunnerKind.WORK_MANAGEMENT_RECONCILIATION,
            mode=RunMode.APPLY,
        )


def test_scheduled_trigger_requires_scheduled_for() -> None:
    with pytest.raises(ValueError, match="scheduled_for"):
        HousekeepingTrigger(
            runner=RunnerKind.BACKLOG_READINESS,
            trigger_kind=TriggerKind.SCHEDULED,
        )


def test_governed_work_links_reads_exact_source_binding(tmp_path: Path) -> None:
    change = tmp_path / ".work" / "changes" / "176-example"
    change.mkdir(parents=True)
    (change / "scope.json").write_text(
        '{"change_id":"176-example","status":"active","complexity":"medium",'
        '"risk_triggers":["external_action"],"work_management":{'
        '"source_repository":"NielPieterse0/kis-mcp","source_number":325,'
        '"source_kind":"issue"}}',
        encoding="utf-8",
    )

    links = governed_work_links(tmp_path)

    assert len(links) == 1
    assert links[0].change_id == "176-example"
    assert links[0].source_key == ("nielpieterse0/kis-mcp", 325, "issue")
    assert links[0].risk_triggers == ("external_action",)
