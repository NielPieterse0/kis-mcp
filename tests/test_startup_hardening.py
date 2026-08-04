from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "src" / "kis_mcp"
ADMINISTRATION_TOOLS = (
    "get_config",
    "set_config_value",
    "get_prompts",
    "get_usage_stats",
    "get_recent_tool_calls",
)


def _source(name: str) -> str:
    return (PACKAGE_ROOT / name).read_text(encoding="utf-8")


def test_provider_compatibility_behavior_is_localized_to_startup_seam() -> None:
    adapter = _source("provider_startup_compat.cjs")
    lifecycle = _source("provider_lifecycle.py")
    configuration = _source("config.py")
    middleware = _source("middleware.py")
    resolver = _source("desktop_commander.py")

    assert "provider_startup_compat.cjs" in lifecycle
    assert "KIS_MCP_PROVIDER_STARTUP_COMPAT" in lifecycle
    assert "PROVIDER_ADMINISTRATION_TOOLS" in adapter
    assert "notifications/message" in adapter
    assert "KIS_MCP_PROVIDER_FLAG_URL" in lifecycle
    assert "tunnel_credential_target" in configuration
    assert "tunnel_authentication_id" not in configuration

    for tool_name in ADMINISTRATION_TOOLS:
        assert tool_name in adapter

    assert "PROVIDER_ADMINISTRATION_TOOLS" not in middleware
    assert "PROVIDER_ADMINISTRATION_TOOLS" not in resolver
    assert "unexposed_tools" not in middleware
    assert "unexposed_tools" not in resolver
    for tool_name in ADMINISTRATION_TOOLS:
        if tool_name != "set_config_value":
            assert tool_name not in middleware
            assert tool_name not in resolver


def test_startup_hardening_does_not_add_policy_rules() -> None:
    policy = (
        REPOSITORY_ROOT / "policy" / "kis-mcp.policy.json"
    ).read_text(encoding="utf-8")

    assert policy.count('"id": "HR-001"') == 1
    assert policy.count('"id": "HR-002"') == 1
    assert policy.count('"id": "HR-003"') == 1
    assert policy.count('"id": "HR-') == 3
