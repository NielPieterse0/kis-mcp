from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kis_mcp.config import load_runtime_config  # noqa: E402
from kis_mcp.provider_contract import (  # noqa: E402
    build_provider_contract,
    contract_fingerprint,
    verify_adapter_contract,
    verify_provider_identity,
)
from kis_mcp.provider_readiness import validate_provider_offline_readiness  # noqa: E402
from kis_mcp.server import _ensure_state_directories, _provider_environment  # noqa: E402


def _json_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json", by_alias=True, exclude_none=True)
        return dict(dumped) if isinstance(dumped, dict) else {}
    return dict(value) if isinstance(value, dict) else {}


def _normalize_tool(tool: Any) -> dict[str, Any]:
    input_schema = getattr(tool, "inputSchema", None)
    if input_schema is None:
        input_schema = getattr(tool, "input_schema", None)
    output_schema = getattr(tool, "outputSchema", None)
    if output_schema is None:
        output_schema = getattr(tool, "output_schema", None)
    normalized: dict[str, Any] = {
        "annotations": _json_mapping(getattr(tool, "annotations", None)),
        "input_schema": _json_mapping(input_schema),
        "name": str(tool.name),
    }
    rendered_output = _json_mapping(output_schema)
    if rendered_output:
        normalized["output_schema"] = rendered_output
    return normalized


async def capture() -> tuple[Path, Path, str, int]:
    config = load_runtime_config(ROOT)
    validate_provider_offline_readiness(config)
    _ensure_state_directories(config)
    launch = config.desktop_commander_launch
    transport = StdioTransport(
        command=str(launch["command"]),
        args=[str(value) for value in launch.get("args", [])],
        cwd=str(launch["cwd"]),
        env=_provider_environment(config),
    )

    async with Client(transport) as client:
        tools = await client.list_tools()

    document = build_provider_contract(
        package=config.desktop_commander_package,
        version=config.desktop_commander_version,
        tools=[_normalize_tool(tool) for tool in tools],
    )
    verify_provider_identity(
        document,
        package=config.desktop_commander_package,
        version=config.desktop_commander_version,
    )
    verify_adapter_contract(document)

    contract_root = ROOT / "contracts" / "desktop-commander"
    contract_root.mkdir(parents=True, exist_ok=True)
    contract_path = contract_root / f"{config.desktop_commander_version}.tools.json"
    fingerprint_path = (
        contract_root / f"{config.desktop_commander_version}.schema.sha256"
    )
    fingerprint = contract_fingerprint(document)
    contract_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fingerprint_path.write_text(fingerprint + "\n", encoding="utf-8")
    return contract_path, fingerprint_path, fingerprint, len(document["tools"])


def main() -> int:
    contract_path, fingerprint_path, fingerprint, tool_count = asyncio.run(
        asyncio.wait_for(capture(), timeout=45)
    )
    print(
        json.dumps(
            {
                "contract": str(contract_path),
                "fingerprint": fingerprint,
                "fingerprint_file": str(fingerprint_path),
                "provider_tools": tool_count,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
