from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from kis_mcp.providers.context7 import load_context7_settings
from kis_mcp.providers.serena import load_serena_settings
from kis_mcp.providers.serena.memory import quarantine_serena_memory_delete
from kis_mcp.quarantine import QuarantineService

STATE = Path(r"C:\Projects\.kis-mcp")
EXPECTED_CONTEXT7 = {"resolve-library-id", "query-docs"}
EXPECTED_SERENA = {
    "activate_project",
    "get_symbols_overview",
    "find_symbol",
    "find_referencing_symbols",
    "list_memories",
    "read_memory",
    "delete_memory",
}


def _text(result: Any) -> str:
    return "\n".join(
        str(getattr(block, "text", ""))
        for block in getattr(result, "content", ())
        if getattr(block, "text", None) is not None
    ).strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _minimal_environment() -> dict[str, str]:
    return {
        key: os.environ[key]
        for key in ("PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT")
        if os.environ.get(key)
    }


async def _context7_smoke() -> dict[str, Any]:
    settings = load_context7_settings(ROOT / "settings/providers/context7.provider.json")
    environment = _minimal_environment()
    api_key = os.environ.get("CONTEXT7_API_KEY", "").strip()
    if api_key:
        environment["CONTEXT7_API_KEY"] = api_key
    transport = StdioTransport(
        command=settings.executable,
        args=[str(settings.entry_point), *settings.arguments],
        cwd=str(ROOT),
        env=environment,
    )
    async with Client(transport, timeout=60, init_timeout=60) as client:
        tools = await client.list_tools()
    names = {tool.name for tool in tools}
    return {
        "status": "passed" if EXPECTED_CONTEXT7.issubset(names) else "failed",
        "package_version": settings.package_version,
        "source_revision": settings.source_revision,
        "tool_count": len(names),
        "required_tools": sorted(EXPECTED_CONTEXT7),
        "required_tools_present": sorted(EXPECTED_CONTEXT7 & names),
        "external_document_query_exercised": False,
        "reason": "Commissioning validates local MCP startup/discovery without bypassing KIS network policy.",
    }


def _serena_environment(settings) -> dict[str, str]:
    environment = _minimal_environment()
    environment.update(
        {
            "HOME": str(settings.home_root),
            "USERPROFILE": str(settings.home_root),
            "APPDATA": str(settings.home_root / "AppData" / "Roaming"),
            "LOCALAPPDATA": str(settings.home_root / "AppData" / "Local"),
            "TEMP": str(settings.temp_root),
            "TMP": str(settings.temp_root),
            "SERENA_USAGE_REPORTING": "false",
            "UV_OFFLINE": "1",
        }
    )
    return environment


def _serena_transport(settings, project: Path) -> StdioTransport:
    return StdioTransport(
        command=str(settings.executable),
        args=list(settings.arguments),
        cwd=str(project),
        env=_serena_environment(settings),
    )


async def _serena_session(settings, project: Path, memory_name: str) -> dict[str, Any]:
    transport = _serena_transport(settings, project)
    async with Client(transport, timeout=120, init_timeout=120) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools}
        activation = await client.call_tool("activate_project", {"project": str(project)})
        overview = await client.call_tool(
            "get_symbols_overview",
            {"relative_path": "sample.py", "depth": 0, "max_answer_chars": 4000},
        )
        memories = await client.call_tool("list_memories", {})
        memory = await client.call_tool("read_memory", {"memory_name": memory_name})
    return {
        "tool_count": len(names),
        "required_tools_present": sorted(EXPECTED_SERENA & names),
        "activation_error": bool(getattr(activation, "is_error", False)),
        "overview_error": bool(getattr(overview, "is_error", False)),
        "overview_excerpt": _text(overview)[:1000],
        "memories": _text(memories),
        "memory": _text(memory),
    }


async def _serena_smoke() -> dict[str, Any]:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    project = STATE / "commissioning" / f"084-serena-{run_id}"
    project.mkdir(parents=True, exist_ok=False)
    (project / "sample.py").write_text(
        "class Commissioned:\n    pass\n\ndef meaning():\n    return 42\n",
        encoding="utf-8",
    )
    memory_name = "084-proof"
    memory_path = project / ".serena" / "memories" / f"{memory_name}.md"
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text("serena hr3-07 live proof\n", encoding="utf-8")
    before_hash = _sha256(memory_path)
    first = await _serena_session(settings, project, memory_name)

    quarantine = QuarantineService(
        project_boundary=settings.project_boundary,
        quarantine_root=str(STATE / "quarantine"),
    )
    quarantined = quarantine_serena_memory_delete(
        settings,
        memory_name,
        project_root=str(project),
        quarantine=quarantine,
    )
    if not quarantined.records:
        raise RuntimeError("Serena HR3-07 live proof did not quarantine the memory artifact")
    missing_after_quarantine = not memory_path.exists()
    restored = quarantine.restore(quarantined.records[0].operation_id)
    restored_hash = _sha256(memory_path)
    second = await _serena_session(settings, project, memory_name)
    memories_after = sorted(
        str(path.relative_to(memory_path.parent).with_suffix("")).replace("\\", "/")
        for path in memory_path.parent.rglob("*.md")
    )
    passed = all(
        (
            EXPECTED_SERENA.issubset(set(first["required_tools_present"])),
            not first["activation_error"],
            not first["overview_error"],
            memory_name in first["memories"],
            missing_after_quarantine,
            quarantined.forwarded_delete is False,
            restored.original_path == str(memory_path),
            restored_hash == before_hash,
            memory_name in second["memories"],
            second["memory"].strip() == "serena hr3-07 live proof",
            memories_after == [memory_name],
        )
    )
    return {
        "status": "passed" if passed else "failed",
        "package_version": settings.package_version,
        "source_revision": settings.source_revision,
        "offline_enforced": True,
        "project": str(project),
        "memory_artifacts": list(quarantined.artifacts),
        "quarantine_operation_id": quarantined.records[0].operation_id,
        "forwarded_delete": quarantined.forwarded_delete,
        "restored_sha256_matches": restored_hash == before_hash,
        "post_restart_memories": memories_after,
        "first_session": first,
        "second_session": second,
    }


async def _run() -> dict[str, Any]:
    context7 = await _context7_smoke()
    serena = await _serena_smoke()
    return {
        "schema_version": 1,
        "change_id": "084-discover-persistent-memory-closeout",
        "generated_at": datetime.now(UTC).isoformat(),
        "context7": context7,
        "serena": serena,
        "status": (
            "passed"
            if context7["status"] == "passed" and serena["status"] == "passed"
            else "failed"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = asyncio.run(_run())
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
