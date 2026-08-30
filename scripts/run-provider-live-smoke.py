from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from kis_mcp.projects import load_project_registry_settings
from kis_mcp.providers.context7 import load_context7_settings
from kis_mcp.providers.serena import load_serena_settings
from kis_mcp.providers.serena.adapter import (
    _prepare_serena_project_state,
    _provider_environment,
    resolve_managed_pyright_launcher,
)
from kis_mcp.providers.serena.memory import quarantine_serena_memory_delete
from kis_mcp.quarantine import QuarantineService
from kis_mcp.repositories import load_repository_settings
from kis_mcp.server import build_server

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
GITHUB_REQUIRED_OPERATIONS = (
    "github_get_me",
    "github_get_file_contents",
    "github_create_or_update_file",
)
SUPABASE_REQUIRED_OPERATIONS = (
    "supabase_get_project_url",
    "supabase_list_tables",
    "supabase_apply_migration",
)


def _text(result: Any) -> str:
    return "\n".join(
        str(getattr(block, "text", ""))
        for block in getattr(result, "content", ())
        if getattr(block, "text", None) is not None
    ).strip()


def _result_mapping(result: Any) -> dict[str, Any]:
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return dict(data)
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        nested = structured.get("result")
        if isinstance(nested, dict):
            return dict(nested)
        return dict(structured)
    text = _text(result)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _provider_mounted(status: dict[str, Any], provider_id: str) -> bool:
    providers = status.get("external_providers")
    return isinstance(providers, list) and any(
        isinstance(item, dict)
        and item.get("provider_id") == provider_id
        and item.get("mounted") is True
        and item.get("state") == "mounted"
        for item in providers
    )


async def _require_operation(client: Any, operation: str) -> None:
    result = await client.call_tool(
        "search_capabilities", {"query": operation, "limit": 20}
    )
    payload = _result_mapping(result)
    operations = payload.get("operations")
    match = next(
        (
            item
            for item in operations or ()
            if isinstance(item, dict) and item.get("operation_name") == operation
        ),
        None,
    )
    if not isinstance(match, dict) or match.get("eligible") is not True:
        raise RuntimeError(f"Shared runtime operation is unavailable: {operation}")


async def _external_call(
    client: Any,
    operation: str,
    arguments: dict[str, Any],
    *,
    raise_on_error: bool = True,
) -> Any:
    return await client.call_tool(
        "execute_external_action",
        {"operation": operation, "arguments": arguments},
        raise_on_error=raise_on_error,
    )


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


def _serena_transport(settings, project: Path) -> StdioTransport:
    environment = _provider_environment(settings, os.environ)
    _prepare_serena_project_state(
        settings,
        environment=environment,
        project_root=str(project),
        pyright_launcher=resolve_managed_pyright_launcher(settings),
    )
    return StdioTransport(
        command=str(settings.executable),
        args=list(settings.arguments),
        cwd=str(project),
        env=environment,
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
    project = STATE / "commissioning" / f"088-serena-{run_id}"
    project.mkdir(parents=True, exist_ok=False)
    (project / "sample.py").write_text(
        "class Commissioned:\n    pass\n\ndef meaning():\n    return 42\n",
        encoding="utf-8",
    )
    memory_name = "088-proof"
    memory_path = settings.project_data_path(str(project)) / "memories" / f"{memory_name}.md"
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
    repo_local_state_absent = not (project / ".serena").exists()
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
            repo_local_state_absent,
            memories_after == [memory_name],
        )
    )
    return {
        "status": "passed" if passed else "failed",
        "package_version": settings.package_version,
        "source_revision": settings.source_revision,
        "offline_enforced": True,
        "project": str(project),
        "project_state": str(settings.project_data_path(str(project))),
        "repo_local_state_absent": repo_local_state_absent,
        "memory_artifacts": list(quarantined.artifacts),
        "quarantine_operation_id": quarantined.records[0].operation_id,
        "forwarded_delete": quarantined.forwarded_delete,
        "restored_sha256_matches": restored_hash == before_hash,
        "post_restart_memories": memories_after,
        "first_session": first,
        "second_session": second,
    }


async def _github_shared_runtime_smoke(server: Any) -> dict[str, Any]:
    repository = load_repository_settings()
    coordinate = repository.github_repository.split("/", 1)
    if len(coordinate) != 2 or not all(part.strip() for part in coordinate):
        raise RuntimeError("Registered GitHub repository coordinate is invalid")
    owner, repo = coordinate
    async with Client(server, timeout=120, init_timeout=120) as client:
        status = _result_mapping(await client.call_tool("kis_provider_status", {}))
        if not _provider_mounted(status, "github-mcp"):
            raise RuntimeError("GitHub MCP provider is not mounted in the shared runtime")
        for operation in GITHUB_REQUIRED_OPERATIONS:
            await _require_operation(client, operation)
        await _external_call(client, "github_get_me", {})
        await _external_call(
            client,
            "github_get_file_contents",
            {"owner": owner, "repo": repo, "path": "README.md"},
        )
        rejected = await _external_call(
            client,
            "github_get_file_contents",
            {"owner": "github", "repo": "github-mcp-server", "path": "README.md"},
            raise_on_error=False,
        )
        if not getattr(rejected, "is_error", False):
            raise RuntimeError("GitHub MCP repository scope was not enforced")
    return {
        "ready": True,
        "mounted": True,
        "surface": True,
        "authentication": True,
        "private_repository_read": True,
        "repository_scope": True,
    }


async def _supabase_shared_runtime_smoke(server: Any) -> dict[str, Any]:
    registry = load_project_registry_settings()
    project_id = registry.default_project_id
    if not project_id:
        raise RuntimeError("Project registry has no default project")
    project = registry.project(project_id)
    if project is None:
        raise RuntimeError("Default registered project could not be resolved")
    if project.supabase is None:
        raise RuntimeError("Default registered project has no Supabase binding")
    project_ref = project.supabase.project_ref
    async with Client(server, timeout=120, init_timeout=120) as client:
        status = _result_mapping(await client.call_tool("kis_provider_status", {}))
        if not _provider_mounted(status, "supabase"):
            raise RuntimeError("Supabase MCP provider is not mounted in the shared runtime")
        for operation in SUPABASE_REQUIRED_OPERATIONS:
            await _require_operation(client, operation)
        result = await _external_call(
            client, "supabase_get_project_url", {"project_id": project_ref}
        )
        value = _result_mapping(result).get("url")
        parsed = urlparse(value) if isinstance(value, str) else None
        expected = f"{project_ref}.supabase.co".lower()
        if parsed is None or parsed.scheme != "https" or (parsed.hostname or "").lower() != expected:
            raise RuntimeError("Supabase MCP registered project read did not match the configured project")
    return {
        "ready": True,
        "mounted": True,
        "account_surface": True,
        "authentication": True,
        "registered_project_read": True,
    }


async def _run() -> dict[str, Any]:
    context7 = await _context7_smoke()
    serena = await _serena_smoke()
    return {
        "schema_version": 1,
        "change_id": "088-serena-project-state-relocation",
        "generated_at": datetime.now(UTC).isoformat(),
        "context7": context7,
        "serena": serena,
        "status": (
            "passed"
            if context7["status"] == "passed" and serena["status"] == "passed"
            else "failed"
        ),
    }


SharedRunner = Callable[[Any], Awaitable[dict[str, Any]]]
SHARED_RUNTIME_RUNNERS: dict[str, SharedRunner] = {
    "github": _github_shared_runtime_smoke,
    "supabase": _supabase_shared_runtime_smoke,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("provider", nargs="?", choices=tuple(SHARED_RUNTIME_RUNNERS))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.provider is None:
        result = asyncio.run(_run())
        passed = result["status"] == "passed"
    else:
        server = build_server()
        result = asyncio.run(SHARED_RUNTIME_RUNNERS[args.provider](server))
        passed = result.get("ready") is True and result.get("mounted") is True
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
