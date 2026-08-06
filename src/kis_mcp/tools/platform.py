from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from ..contracts import ProviderCapabilities, ProviderEffectResolver
from ..models import InvocationEffects
from .context7 import Context7Settings, context7_tool_descriptor
from .context7.adapter import ProxyFactory as Context7ProxyFactory
from .serena import SerenaEffectResolver, SerenaSettings, serena_tool_descriptor
from .serena.adapter import ProxyFactory as SerenaProxyFactory


class ToolMountState(StrEnum):
    DISABLED = "disabled"
    SETTINGS_FAILED = "settings_failed"
    BUILD_FAILED = "build_failed"
    INVALID_BUILDER_RESULT = "invalid_builder_result"
    MOUNT_FAILED = "mount_failed"
    MOUNTED = "mounted"


@dataclass(frozen=True, slots=True)
class ToolMountResult:
    tool_id: str
    namespace: str
    enabled: bool
    built: bool
    mounted: bool
    state: ToolMountState
    error_type: str | None = None


class _InactiveSerenaEffectResolver:
    def __init__(self) -> None:
        self._capabilities = ProviderCapabilities(
            network_only_tools=frozenset(),
            direct_delete_tools=frozenset(),
            unexposed_tool_arguments={},
            unexposed_config_keys=frozenset(),
            configuration_tool_name=None,
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def resolve(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None,
    ) -> InvocationEffects:
        return InvocationEffects()

    def observe_success(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None,
        result: Any,
    ) -> None:
        return None


class CompositeToolEffectResolver:
    def __init__(
        self,
        desktop_resolver: ProviderEffectResolver,
        serena_resolver: ProviderEffectResolver,
    ) -> None:
        self.desktop_resolver = desktop_resolver
        self.serena_resolver = serena_resolver
        desktop = desktop_resolver.capabilities
        serena = serena_resolver.capabilities
        self._capabilities = ProviderCapabilities(
            network_only_tools=frozenset(
                set(desktop.network_only_tools) | set(serena.network_only_tools)
            ),
            direct_delete_tools=frozenset(
                set(desktop.direct_delete_tools) | set(serena.direct_delete_tools)
            ),
            unexposed_tool_arguments={
                **desktop.unexposed_tool_arguments,
                **serena.unexposed_tool_arguments,
            },
            unexposed_config_keys=frozenset(
                set(desktop.unexposed_config_keys)
                | set(serena.unexposed_config_keys)
            ),
            configuration_tool_name=desktop.configuration_tool_name,
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def resolve(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None,
    ) -> InvocationEffects:
        if tool_name.casefold().startswith("serena_"):
            return self.serena_resolver.resolve(tool_name, arguments)
        return self.desktop_resolver.resolve(tool_name, arguments)

    def observe_success(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None,
        result: Any,
    ) -> None:
        if tool_name.casefold().startswith("serena_"):
            observer = getattr(self.serena_resolver, "observe_success", None)
            if callable(observer):
                observer(tool_name, arguments, result)
            return
        observer = getattr(self.desktop_resolver, "observe_success", None)
        if callable(observer):
            observer(tool_name, arguments, result)


@dataclass(frozen=True, slots=True)
class ToolRuntimeComposition:
    resolver: CompositeToolEffectResolver
    results: tuple[ToolMountResult, ...]


def _mount_adapter(
    server: FastMCP,
    *,
    tool_id: str,
    namespace: str,
    enabled: bool,
    adapter_builder: Any,
) -> ToolMountResult:
    if not enabled:
        return ToolMountResult(
            tool_id=tool_id,
            namespace=namespace,
            enabled=False,
            built=False,
            mounted=False,
            state=ToolMountState.DISABLED,
        )
    try:
        adapter = adapter_builder()
        provider = adapter.build_server()
    except Exception as exc:
        return ToolMountResult(
            tool_id=tool_id,
            namespace=namespace,
            enabled=True,
            built=False,
            mounted=False,
            state=ToolMountState.BUILD_FAILED,
            error_type=type(exc).__name__,
        )
    if not isinstance(provider, FastMCP):
        return ToolMountResult(
            tool_id=tool_id,
            namespace=namespace,
            enabled=True,
            built=False,
            mounted=False,
            state=ToolMountState.INVALID_BUILDER_RESULT,
            error_type=type(provider).__name__,
        )
    try:
        server.mount(provider, namespace=namespace)
    except Exception as exc:
        return ToolMountResult(
            tool_id=tool_id,
            namespace=namespace,
            enabled=True,
            built=True,
            mounted=False,
            state=ToolMountState.MOUNT_FAILED,
            error_type=type(exc).__name__,
        )
    return ToolMountResult(
        tool_id=tool_id,
        namespace=namespace,
        enabled=True,
        built=True,
        mounted=True,
        state=ToolMountState.MOUNTED,
    )


def compose_tool_runtime(
    server: FastMCP,
    desktop_resolver: ProviderEffectResolver,
    *,
    project_root: Path,
    repository_root: Path | None = None,
    environment: Mapping[str, str] | None = None,
    context7_proxy_factory: Context7ProxyFactory | None = None,
    serena_proxy_factory: SerenaProxyFactory | None = None,
) -> ToolRuntimeComposition:
    root = (repository_root or Path(__file__).resolve().parents[3]).resolve()
    env = environment or os.environ
    results: list[ToolMountResult] = []

    try:
        context7_settings = Context7Settings.load(
            root / "settings" / "tools" / "context7.tool.json"
        )
        context7 = context7_tool_descriptor(
            context7_settings,
            environment=env,
            proxy_factory=context7_proxy_factory,
        )
        results.append(
            _mount_adapter(
                server,
                tool_id=context7.tool_id,
                namespace=context7_settings.namespace,
                enabled=context7.enabled,
                adapter_builder=context7.builder,
            )
        )
    except Exception as exc:
        results.append(
            ToolMountResult(
                tool_id="context7-mcp",
                namespace="context7",
                enabled=True,
                built=False,
                mounted=False,
                state=ToolMountState.SETTINGS_FAILED,
                error_type=type(exc).__name__,
            )
        )

    serena_resolver: ProviderEffectResolver = _InactiveSerenaEffectResolver()
    try:
        serena_settings = SerenaSettings.load(
            root / "settings" / "tools" / "serena.tool.json"
        )
        serena_resolver = SerenaEffectResolver(
            serena_settings,
            project_root=str(project_root),
        )
        serena = serena_tool_descriptor(
            serena_settings,
            environment=env,
            proxy_factory=serena_proxy_factory,
        )
        results.append(
            _mount_adapter(
                server,
                tool_id=serena.tool_id,
                namespace=serena_settings.namespace,
                enabled=serena.enabled,
                adapter_builder=serena.builder,
            )
        )
    except Exception as exc:
        results.append(
            ToolMountResult(
                tool_id="serena-mcp",
                namespace="serena",
                enabled=True,
                built=False,
                mounted=False,
                state=ToolMountState.SETTINGS_FAILED,
                error_type=type(exc).__name__,
            )
        )

    return ToolRuntimeComposition(
        resolver=CompositeToolEffectResolver(desktop_resolver, serena_resolver),
        results=tuple(sorted(results, key=lambda item: item.tool_id)),
    )


__all__ = [
    "CompositeToolEffectResolver",
    "ToolMountResult",
    "ToolMountState",
    "ToolRuntimeComposition",
    "compose_tool_runtime",
]