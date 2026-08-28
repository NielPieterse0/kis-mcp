from __future__ import annotations

import json
from itertools import islice
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.config import RuntimeConfig
from kis_mcp.projects import load_project_registry_settings
from kis_mcp.state import StateDiagnosticsService, derive_worktree_source_id

_LOCAL_READ = {
    "read_only_hint": True,
    "destructive_hint": False,
    "idempotent_hint": True,
    "open_world_hint": False,
}
_LOCAL_MUTATION = {
    "read_only_hint": False,
    "destructive_hint": False,
    "idempotent_hint": True,
    "open_world_hint": False,
}


def _tool_error(code: str, exc: Exception) -> ToolError:
    return ToolError(json.dumps({"error_code": code, "reason": str(exc)}, sort_keys=True))


def _current_sources() -> dict[str, set[str]]:
    registry = load_project_registry_settings()
    current_sources: dict[str, set[str]] = {}
    for project in registry.projects:
        sources = {derive_worktree_source_id(project.local_root)}
        worktrees = Path(project.local_root) / ".work" / "worktrees"
        if worktrees.is_dir():
            try:
                candidates = list(islice(worktrees.iterdir(), 513))
            except OSError:
                sources.add("*")
            else:
                candidates.sort(key=lambda item: item.name.casefold())
                if len(candidates) > 512:
                    sources.add("*")
                for path in candidates[:512]:
                    if path.is_dir():
                        sources.add(derive_worktree_source_id(str(path)))
        current_sources[project.project_id] = sources
    return current_sources


def build_state_diagnostics_service(runtime: RuntimeConfig) -> StateDiagnosticsService:
    registry = load_project_registry_settings()
    project_roots = {project.project_id: Path(project.local_root) for project in registry.projects}
    return StateDiagnosticsService(
        state_root=Path(runtime.state_root),
        project_boundary=Path(runtime.project_boundary),
        quarantine_root=Path(runtime.quarantine_root),
        current_sources_provider=_current_sources,
        project_roots=project_roots,
    )


def register_state_management_tools(server: FastMCP, runtime: RuntimeConfig) -> None:
    service = build_state_diagnostics_service(runtime)
    tool_server = FastMCP("kis-mcp-state-management")

    @tool_server.tool(annotations=_LOCAL_READ)
    async def state_ownership_inventory(limit: int = 200) -> dict[str, object]:
        """Inspect bounded canonical state ownership and stale-state safety diagnostics."""
        try:
            return service.inventory(limit=limit).to_json_dict()
        except Exception as exc:
            raise _tool_error("STATE_OWNERSHIP_INVENTORY_FAILED", exc) from exc

    @tool_server.tool(annotations=_LOCAL_MUTATION)
    async def state_stale_cleanup(
        relative_path: str,
        apply: bool = False,
        idempotency_key: str | None = None,
        preview_token: str | None = None,
    ) -> dict[str, object]:
        """Preview or quarantine one proven-stale reconstructible state namespace."""
        try:
            if apply and (not isinstance(idempotency_key, str) or not idempotency_key.strip()):
                raise ValueError("idempotency_key is required when apply is true")
            result = service.cleanup(
                relative_path,
                apply=apply,
                idempotency_key=idempotency_key,
                preview_token=preview_token,
            )
            if idempotency_key is not None:
                result["idempotency_key"] = idempotency_key.strip()
            return result
        except Exception as exc:
            raise _tool_error("STATE_STALE_CLEANUP_FAILED", exc) from exc

    server.mount(tool_server)


__all__ = ["build_state_diagnostics_service", "register_state_management_tools"]
