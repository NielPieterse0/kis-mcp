from __future__ import annotations

import argparse
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "housekeeping.py"
SPEC = importlib.util.spec_from_file_location("housekeeping_script", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
housekeeping = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(housekeeping)


def test_main_builds_server_before_entering_asyncio(monkeypatch) -> None:
    args = argparse.Namespace(
        runner="work-management-reconciliation",
        project_id="kis-mcp",
        repository="NielPieterse0/kis-mcp",
        repository_root=housekeeping.ROOT,
        mode="preview",
        trigger_kind="manual",
        trigger_id="manual",
        scheduled_for=None,
        idempotency_key=None,
        item_limit=100,
        max_findings=10,
        max_mutations=5,
        max_external_reads=5,
    )
    parser = SimpleNamespace(parse_args=lambda: args)
    monkeypatch.setattr(housekeeping, "_parser", lambda: parser)

    def build_server():
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return object()
        raise AssertionError("build_server must run before asyncio.run")

    monkeypatch.setattr(housekeeping, "build_server", build_server)
    monkeypatch.setattr(housekeeping, "FastMCPInvoker", lambda server: server)

    async def fake_runner(invoker, config, trigger):
        assert config.project_id == "kis-mcp"
        assert trigger.runner.value == "work_management_reconciliation"
        return SimpleNamespace(
            complete=True,
            to_json_dict=lambda: {"complete": True, "runner": trigger.runner.value},
        )

    monkeypatch.setattr(
        housekeeping, "run_work_management_reconciliation", fake_runner
    )

    assert housekeeping.main() == 0
