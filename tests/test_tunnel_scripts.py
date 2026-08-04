from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY_ROOT / "scripts"


def _script(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8")


def test_tunnel_configuration_is_canonical_json() -> None:
    settings = json.loads(
        (REPOSITORY_ROOT / "settings" / "kis-mcp.settings.json").read_text(
            encoding="utf-8"
        )
    )
    remote = settings["remote_mcp"]

    assert remote["tunnel_client_path"] == (
        r"C:\Tools\openai-tunnel-client\tunnel-client.exe"
    )
    assert set(remote["instances"]) == {"operation", "development"}
    for instance in remote["instances"].values():
        assert "tunnel_id" in instance
        assert "tunnel_authentication_id" in instance
        assert "configured" not in instance


def test_tunnel_state_helper_reads_settings_and_named_instances() -> None:
    content = _script("tunnel-state.ps1")

    assert "settings\\kis-mcp.settings.json" in content
    assert "Get-KisMcpRemoteInstance" in content
    assert "operation" in content and "development" in content
    assert "tunnel_authentication_id" in content
    assert "tunnel_client_path" in content


def test_setup_script_materializes_authentication_identifier_without_environment_dependency() -> None:
    content = _script("setup-tunnel.ps1")

    assert "Get-KisMcpRemoteInstance" in content
    assert "--profile-dir" in content
    assert "--tunnel-id" in content
    assert "--mcp-server-url" in content
    assert "--control-plane-api-key-ref" in content
    assert '"file:$($Remote.tunnel_authentication_path)"' in content
    assert "[System.IO.File]::WriteAllText" in content
    assert "$Remote.tunnel_authentication_id" in content
    assert "BackupExistingProfile" in content
    assert "doctor" in content
    assert "--explain" in content
    assert "CONTROL_PLANE_API_KEY" not in content
    assert "env:" not in content
    assert "sk-" not in content


def test_chatgpt_launcher_owns_http_and_tunnel_processes() -> None:
    content = _script("start-chatgpt.ps1")

    assert "ValidateSet('operation', 'development')" in content
    assert "kis_mcp.remote_runtime" in content
    assert "--mcp.server-url" in content
    assert "--health.url-file" in content
    assert "readyz" in content
    assert "Kill()" in content
    assert "tunnel_authentication_id" in content
    assert "KIS_MCP_OTHER_INSTANCE_ACTIVE" in content


def test_smoke_script_checks_full_representative_tool_surface() -> None:
    content = _script("smoke-chatgpt.ps1")

    assert "initialize" in content
    assert "tools/list" in content
    assert "tools/call" in content
    for tool_name in (
        "kis_health",
        "read_file",
        "write_file",
        "edit_block",
        "start_process",
    ):
        assert tool_name in content
    assert "give_feedback_to_desktop_commander" in content
    assert "KIS_MCP_SMOKE_NETWORK_ONLY_TOOL_EXPOSED" in content
    assert "PSObject.Properties['error']" in content
    assert "kis_quarantine_path" in content
    assert "KIS_MCP_SMOKE_WRITE_CALL_FAILED" in content
    assert "KIS_MCP_SMOKE_READ_CALL_FAILED" in content
    assert "KIS_MCP_SMOKE_QUARANTINE_CALL_FAILED" in content
    assert "KIS_MCP_SMOKE_CLEANUP_QUARANTINE_FAILED" in content
