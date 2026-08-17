from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from kis_mcp.execution.local_state import reconcile_stale_runs
from kis_mcp.execution.settings import LocalProcessProfileSettings


def test_stale_nonterminal_run_is_cancelled_and_never_authoritative() -> None:
    root = Path(r"C:\Projects\.kis-mcp\temp") / f"local-state-test-{uuid.uuid4().hex}"
    run = root / "runs" / "stale-run"
    run.mkdir(parents=True)
    (run / "state.json").write_text(
        json.dumps({
            "schema_version": 1,
            "request_id": "stale-run",
            "owner_pid": 2147483647,
            "status": "executing",
            "authoritative": True,
        }),
        encoding="utf-8",
    )
    settings = LocalProcessProfileSettings(
        state_root=str(root),
        materialize_timeout_ms=30_000,
        worker_cleanup_grace_ms=5_000,
    )
    try:
        assert reconcile_stale_runs(settings) == ("stale-run",)
        state = json.loads((run / "state.json").read_text(encoding="utf-8"))
        assert state["status"] == "reconciliation_requested"
        assert state["authoritative"] is False
        assert (run / "cancel.requested").is_file()
    finally:
        shutil.rmtree(root, ignore_errors=True)
