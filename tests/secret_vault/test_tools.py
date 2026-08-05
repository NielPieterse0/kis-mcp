from __future__ import annotations

import asyncio
from pathlib import Path

from fastmcp import FastMCP

from kis_mcp.secrets.contracts import KdfParameters
from kis_mcp.secrets.service import SecretsService
from kis_mcp.secrets.tools import SECRETS_TOOL_NAMES, register_secret_tools
from kis_mcp.secrets.vault import VaultStore


REFERENCE = "secret://providers/nvidia/api-key"
SECRET = "mcp-must-never-return-this-marker"


def _server(tmp_path: Path) -> tuple[FastMCP, SecretsService]:
    service = SecretsService(
        VaultStore(tmp_path / "secrets"),
        kdf_parameters=KdfParameters(iterations=1, memory_cost_kib=8192, lanes=1),
    )
    service.initialize("master-passphrase", {REFERENCE: SECRET})
    server = FastMCP("secrets-test")
    returned = register_secret_tools(server, service)
    assert returned is service
    return server, service


def test_registers_exact_metadata_only_tool_surface(tmp_path: Path) -> None:
    server, _ = _server(tmp_path)

    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}

    assert names == set(SECRETS_TOOL_NAMES)
    assert SECRETS_TOOL_NAMES == (
        "kis_secret_status",
        "kis_list_secret_references",
        "kis_lock_secrets",
    )
    for tool in tools:
        assert tool.parameters["properties"] == {}
        serialized = repr(tool.parameters).casefold() + repr(tool.output_schema).casefold()
        assert "secret_value" not in serialized
        assert "passphrase" not in serialized
        assert "plaintext" not in serialized


def test_public_operations_never_return_plaintext(tmp_path: Path) -> None:
    server, service = _server(tmp_path)

    status = asyncio.run(server.call_tool("kis_secret_status", {}))
    listed = asyncio.run(server.call_tool("kis_list_secret_references", {}))
    locked = asyncio.run(server.call_tool("kis_lock_secrets", {}))

    combined = repr(status.structured_content) + repr(listed.structured_content) + repr(locked.structured_content)
    assert SECRET not in combined
    assert listed.structured_content["references"][0]["reference"] == REFERENCE
    assert locked.structured_content["unlocked"] is False
    assert service.status().unlocked is False
