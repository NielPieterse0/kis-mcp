from __future__ import annotations

from pathlib import Path

from kis_mcp.state import resolve_runtime_state_path


def test_runtime_state_paths_are_canonically_isolated() -> None:
    state_root = Path("C:/Projects/.kis-mcp")

    op = resolve_runtime_state_path(
        state_root,
        runtime_instance_id="kis-op",
        state_key="housekeeping",
    )
    dev = resolve_runtime_state_path(
        state_root,
        runtime_instance_id="kis-dev",
        state_key="housekeeping",
    )

    assert op == state_root / "runtime" / "kis-op" / "state" / "housekeeping"
    assert dev == state_root / "runtime" / "kis-dev" / "state" / "housekeeping"
    assert op != dev
