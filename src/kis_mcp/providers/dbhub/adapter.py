from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path, PureWindowsPath

from fastmcp import FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.server import create_proxy
from fastmcp.server.providers.proxy import ProxyClient

from kis_mcp.projects import DatabaseBinding, ProjectDefinition, ProjectRegistry
from kis_mcp.state import (
    StateNamespaceRequest,
    StateNamespaceResolver,
    StateOwnershipClass,
    derive_worktree_source_id,
)

from .settings import DBHubSettings

ProxyFactory = Callable[[str, tuple[str, ...], dict[str, str]], FastMCP]
_MAX_OPERATION_NAME = 128


def _proxy(command: str, arguments: tuple[str, ...], environment: dict[str, str]) -> FastMCP:
    transport = StdioTransport(command=command, args=list(arguments), cwd=None, env=environment)
    return create_proxy(ProxyClient(transport), name="dbhub-binding")


def binding_namespace(project_id: str, binding_id: str) -> str:
    return f"{project_id.replace('-', '_')}_{binding_id.replace('-', '_')}"


def operation_name(project_id: str, binding_id: str, tool_name: str) -> str:
    value = f"db_{binding_namespace(project_id, binding_id)}_{tool_name}"
    if len(value) > _MAX_OPERATION_NAME:
        raise RuntimeError("DBHub operation name exceeds the supported MCP name contract")
    return value


def internal_dsn_environment(project_id: str, binding_id: str) -> str:
    return f"KIS_MCP_DBHUB_{binding_namespace(project_id, binding_id).upper()}_DSN"


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def _local_sqlite_dsn(project: ProjectDefinition, binding: DatabaseBinding) -> str:
    assert binding.location is not None
    root = PureWindowsPath(project.local_root)
    target = root.joinpath(PureWindowsPath(binding.location))
    if ".." in target.parts:
        raise RuntimeError("DBHub local database path escapes the project root")
    rendered = str(target).replace("\\", "/")
    return f"sqlite:///{rendered}"


def render_binding_toml(
    project: ProjectDefinition,
    binding: DatabaseBinding,
    settings: DBHubSettings,
) -> str:
    dsn = _local_sqlite_dsn(project, binding) if binding.boundary == "local" else "${DBHUB_DSN}"
    lines = [
        "[[sources]]",
        f"id = {_toml_string(binding.binding_id)}",
        f"dsn = {_toml_string(dsn)}",
    ]
    for tool in settings.enabled_tools:
        lines.extend(["", "[[tools]]", f"name = {_toml_string(tool)}", f"source = {_toml_string(binding.binding_id)}"])
        if tool == "execute_sql":
            lines.extend(["readonly = true", f"max_rows = {settings.max_rows}"])
    return "\n".join(lines) + "\n"


def runtime_config_path(
    settings: DBHubSettings,
    project_id: str,
    binding_id: str,
    *,
    source_root: str,
) -> Path:
    namespace = StateNamespaceResolver().resolve(
        StateNamespaceRequest(
            ownership=StateOwnershipClass.RECONSTRUCTIBLE_CACHE,
            state_key="dbhub-runtime-config",
            identities={
                "project_id": project_id,
                "source_id": derive_worktree_source_id(source_root),
            },
        )
    )
    state_root = settings.runtime_root.parent.parent
    return state_root.joinpath(*PureWindowsPath(namespace.relative_path).parts, binding_id, "dbhub.toml")


def write_binding_runtime_config(
    settings: DBHubSettings,
    project: ProjectDefinition,
    binding: DatabaseBinding,
    *,
    source_root: str,
) -> Path:
    path = runtime_config_path(
        settings,
        project.project_id,
        binding.binding_id,
        source_root=source_root,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    content = render_binding_toml(project, binding, settings)
    if path.is_file():
        try:
            if path.read_text(encoding="utf-8") == content:
                return path
        except (OSError, UnicodeError):
            pass
    path.write_text(content, encoding="utf-8", newline="\n")
    return path


def binding_environment(
    project: ProjectDefinition,
    binding: DatabaseBinding,
    environment: Mapping[str, str],
) -> dict[str, str]:
    if binding.boundary == "local":
        return {}
    name = internal_dsn_environment(project.project_id, binding.binding_id)
    value = environment.get(name)
    if not value:
        raise RuntimeError(f"DBHub credential is not commissioned for {project.project_id}/{binding.binding_id}")
    return {"DBHUB_DSN": value}


class DBHubAdapter:
    def __init__(
        self,
        settings: DBHubSettings,
        projects: ProjectRegistry,
        *,
        environment: Mapping[str, str],
        proxy_factory: ProxyFactory = _proxy,
        source_root: str,
    ) -> None:
        self.settings = settings
        self.projects = projects
        self.environment = environment
        self.proxy_factory = proxy_factory
        self.source_root = source_root

    def build_server(self) -> FastMCP:
        server = FastMCP("dbhub")
        for project in self.projects.projects:
            for binding in project.databases:
                config = write_binding_runtime_config(
                    self.settings,
                    project,
                    binding,
                    source_root=self.source_root,
                )
                environment = binding_environment(project, binding, self.environment)
                child = self.proxy_factory(
                    self.settings.node_executable,
                    (
                        str(self.settings.entry_point),
                        "--transport=stdio",
                        f"--config={config}",
                    ),
                    environment,
                )
                server.mount(child, namespace=binding_namespace(project.project_id, binding.binding_id))
        return server


__all__ = [
    "DBHubAdapter",
    "ProxyFactory",
    "binding_environment",
    "binding_namespace",
    "internal_dsn_environment",
    "operation_name",
    "render_binding_toml",
    "runtime_config_path",
    "write_binding_runtime_config",
]
