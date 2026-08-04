from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SUPPORT_ROOT = Path(__file__).resolve().parents[1] / "support"
sys.path.insert(0, str(SUPPORT_ROOT))

from live_proxy_commissioning import (  # noqa: E402
    build_gateway_environment,
    choose_unmounted_drive,
    result_text,
    run_live_commissioning,
    validate_provider_state_bytes,
)


def test_choose_unmounted_drive_prefers_highest_available_letter() -> None:
    existing = {"Z:\\", "Y:\\"}

    selected = choose_unmounted_drive(exists=lambda path: path in existing)

    assert selected == "X:\\"


def test_build_gateway_environment_isolates_generated_state() -> None:
    repository_root = Path(r"C:\Projects\kis-mcp")

    environment = build_gateway_environment(
        repository_root,
        base_environment={"PATH": r"C:\Windows\System32"},
    )

    assert environment["PATH"] == r"C:\Windows\System32"
    assert environment["PYTHONPATH"] == str(repository_root / "src")
    assert environment["TEMP"] == r"C:\Projects\.kis-mcp\temp"
    assert environment["TMP"] == r"C:\Projects\.kis-mcp\temp"
    assert environment["PYTHONPYCACHEPREFIX"] == r"C:\Projects\.kis-mcp\python-cache"
    assert environment["UV_CACHE_DIR"] == r"C:\Projects\.kis-mcp\uv-cache"
    assert environment["NO_UPDATE_NOTIFIER"] == "1"


def test_result_text_joins_text_content_blocks() -> None:
    result = SimpleNamespace(
        content=[
            SimpleNamespace(text="first"),
            SimpleNamespace(value="ignored"),
            SimpleNamespace(text="second"),
        ]
    )

    assert result_text(result) == "first\nsecond"


def test_validate_provider_state_accepts_required_policy_state() -> None:
    validate_provider_state_bytes(
        b'{"blockedCommands": [], "allowedDirectories": [], "telemetryEnabled": false}'
    )


def test_validate_provider_state_rejects_truncated_state() -> None:
    with pytest.raises(AssertionError, match="PROVIDER_STATE_INTEGRITY"):
        validate_provider_state_bytes(b"")


@pytest.mark.skipif(
    os.environ.get("KIS_MCP_LIVE_COMMISSION") != "1",
    reason="set KIS_MCP_LIVE_COMMISSION=1 to run the real stdio commissioning test",
)
def test_live_proxy_commissioning() -> None:
    report = run_live_commissioning(Path(__file__).resolve().parents[2])

    assert set(report) == {
        "health",
        "surface",
        "read",
        "write",
        "hr001",
        "quarantine",
        "restore",
        "process",
        "provider_state",
    }
    assert all(report.values())
