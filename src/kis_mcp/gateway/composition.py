from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastmcp import FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.server.providers.proxy import FastMCPProxy, ProxyClient, ProxyProvider

from ..capabilities.catalogue import CapabilityCatalogue
from ..capabilities.exposure import ExposureMiddleware, ExposurePlanner
from ..capabilities.runtime import CapabilityRuntimeState
from ..capabilities.settings import load_capability_settings
from ..capabilities.surface import capability_control_contribution
from ..capabilities.tools import register_capability_tools
from ..commissioning_runtime.capability import (
    post_merge_commissioning_capability_contribution,
)
from ..commissioning_runtime.platform import compose_post_merge_commissioning_runtime
from ..config import RuntimeConfig, load_runtime_config
from ..desktop_commander import DesktopCommanderEffectResolver
from ..discover.platform import (
    discover_capability_contributions,
    register_platform_discover,
)
from ..housekeeping_runtime.capability import housekeeping_capability_contribution
from ..housekeeping_runtime.platform import compose_housekeeping_runtime
from ..line_endings import RepositoryLineEndingNormalizer
from ..mcp2026 import install_mcp2026_tasks
from ..mcp2026_prompts import (
    DeterministicDiscoveryTransform,
    register_mcp2026_workflow_prompts,
)
from ..middleware import BoundaryObservabilityMiddleware, ThreeRuleMiddleware
from ..policy import ThreeRulePolicy
from ..process_environment import RepositoryProcessEnvironmentNormalizer
from ..projects import load_project_registry_settings
from ..projects.platform import project_capability_contribution, register_project_tools
from ..provider_lifecycle import prepare_provider_launch
from ..provider_readiness import validate_provider_offline_readiness
from ..providers.platform import (
    ProviderRuntimeSettings,
    ProviderService,
    compose_platform_providers,
    provider_capability_contributions,
    provider_runtime_tools,
)
from ..quarantine import QuarantineService
from ..repositories import SelectedRepositorySettings
from ..skills.platform import (
    current_skill_capability_contributions,
    register_platform_skills,
    skills_runtime_status,
)
from ..tools.platform import build_platform_tool_registry, tool_capability_contributions
from ..workflows.platform import (
    load_platform_workflow_settings,
    register_platform_workflows,
    workflow_descriptors,
)
from .context import GatewayComposition
from .foundation import ensure_state_directories, provider_environment
from .operations import quarantine_many_payloads, register_gateway_operations

CreateProxy = Callable[..., FastMCP]
ProviderValidator = Callable[[RuntimeConfig], None]


def _provider_uses_proxy(provider: Any, seen: set[int] | None = None) -> bool:
    visited = set() if seen is None else seen
    identity = id(provider)
    if identity in visited:
        return False
    visited.add(identity)
    if isinstance(provider, ProxyProvider):
        return True
    inner = getattr(provider, "_inner", None)
    if inner is not None and _provider_uses_proxy(inner, visited):
        return True
    child_server = getattr(provider, "server", None)
    if isinstance(child_server, FastMCP):
        return any(
            _provider_uses_proxy(child, visited)
            for child in child_server.providers
        )
    return False


def _run_awaitable_sync(factory: Callable[[], Awaitable[Any]]) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())

    context = copy_context()
    with ThreadPoolExecutor(
        max_workers=1,
        thread_name_prefix="kis-gateway-compose-async",
    ) as executor:
        return executor.submit(context.run, lambda: asyncio.run(factory())).result()


def _listed_safe_tools(server: FastMCP) -> list[Any]:
    tools: list[Any] = []
    for provider in server.providers:
        if _provider_uses_proxy(provider):
            continue
        tools.extend(_run_awaitable_sync(provider.list_tools))
    return tools


def _listed_desktop_commander_tools(
    *,
    launch: dict[str, Any],
    provider_args: list[str],
    environment: dict[str, str],
    create_proxy_fn: CreateProxy,
    server_name: str,
) -> list[Any]:
    transport = StdioTransport(
        command=str(launch["command"]),
        args=list(provider_args),
        cwd=str(launch["cwd"]),
        env=dict(environment),
        keep_alive=False,
    )
    discovery = create_proxy_fn(
        ProxyClient(transport),
        name=f"{server_name}-surface-discovery",
    )
    return list(_run_awaitable_sync(discovery.list_tools))


def _declared_provider_tools(
    contributions: tuple[Any, ...],
    mounted_provider_ids: set[str],
) -> list[Any]:
    return [
        SimpleNamespace(
            name=operation.name,
            description=operation.description,
            annotations=None,
            input_schema=operation.input_schema,
        )
        for contribution in contributions
        if contribution.contribution_id.removeprefix("provider.") in mounted_provider_ids
        for operation in contribution.operations
        if operation.enabled
    ]


def compose_gateway(
    config: RuntimeConfig | None = None,
    *,
    validate_provider: bool = True,
    provider_service: ProviderService | None = None,
    provider_runtime_settings: ProviderRuntimeSettings | None = None,
    create_proxy_fn: CreateProxy,
    provider_validator_fn: ProviderValidator = validate_provider_offline_readiness,
) -> GatewayComposition:
    runtime = config or load_runtime_config()
    agent_settings = load_platform_workflow_settings()
    if validate_provider:
        provider_validator_fn(runtime)
    ensure_state_directories(runtime)

    launch = runtime.desktop_commander_launch
    provider_args, environment = prepare_provider_launch(
        args=launch.get("args", []),
        environment=provider_environment(runtime),
        provider_state_file=runtime.provider_state_file,
    )
    transport = StdioTransport(
        command=str(launch["command"]),
        args=provider_args,
        cwd=str(launch["cwd"]),
        env=environment,
    )
    server = create_proxy_fn(ProxyClient(transport), name=runtime.server_name)
    install_mcp2026_tasks(server)
    server.add_transform(DeterministicDiscoveryTransform())
    register_mcp2026_workflow_prompts(server)
    projects = load_project_registry_settings(boundary=runtime.project_boundary)
    repository_selection = SelectedRepositorySettings(
        registry=projects,
        boundary=Path(runtime.project_boundary),
    )

    register_project_tools(server, projects)
    providers = compose_platform_providers(
        server,
        runtime_config=runtime,
        nvidia_settings=agent_settings.nvidia,
        provider_service=provider_service,
        provider_runtime_settings=provider_runtime_settings,
        environment=os.environ,
        selected_repository=repository_selection,
    )
    register_platform_discover(
        server,
        runtime,
        projects,
        semantic_provider=providers.serena_adapter,
    )

    quarantine = QuarantineService(
        project_boundary=runtime.project_boundary,
        quarantine_root=runtime.quarantine_root,
    )
    component_status: dict[str, str] = {}
    register_gateway_operations(
        server,
        runtime=runtime,
        launch=dict(launch),
        quarantine=quarantine,
        provider_service=providers.service,
        provider_composition=providers.composition,
        component_status=lambda: dict(component_status),
    )
    register_platform_workflows(
        server,
        runtime,
        agent_settings,
        providers.service,
    )
    compose_housekeeping_runtime(
        server,
        runtime,
        environment=os.environ,
    )
    compose_post_merge_commissioning_runtime(
        server,
        runtime,
        environment=os.environ,
    )

    resolver = DesktopCommanderEffectResolver(
        project_boundary=runtime.project_boundary,
        provider_state_file=runtime.provider_state_file,
    )
    policy = ThreeRulePolicy(
        project_boundary=runtime.project_boundary,
        quarantine_root=runtime.quarantine_root,
    )
    server.add_middleware(BoundaryObservabilityMiddleware())
    server.add_middleware(
        ThreeRuleMiddleware(
            resolver=resolver,
            policy=policy,
            quarantine_paths=lambda paths: quarantine_many_payloads(quarantine, paths),
            text_normalizer=RepositoryLineEndingNormalizer(
                project_boundary=runtime.project_boundary
            ),
            process_environment_normalizer=RepositoryProcessEnvironmentNormalizer(
                project_boundary=runtime.project_boundary,
                projects=projects,
            ),
        )
    )
    skill_service, skill_cards = register_platform_skills(
        server,
        state_root=runtime.state_root,
    )
    skills_status = skills_runtime_status(skill_service)
    component_status["skills"] = skills_status.implementation_value()

    settings = load_capability_settings()
    provider_contributions = provider_capability_contributions(
        providers.service,
        providers.composition,
    )
    static_contributions = (
        *provider_contributions,
        *tool_capability_contributions(build_platform_tool_registry()),
        *discover_capability_contributions(),
        project_capability_contribution(),
        housekeeping_capability_contribution(),
        post_merge_commissioning_capability_contribution(),
        capability_control_contribution(),
    )
    def current_skill_contributions():
        return current_skill_capability_contributions(
            skill_service,
            skill_cards,
            settings,
        )
    base_contributions = (*static_contributions, *current_skill_contributions())
    namespaces = {
        item.provider_id: item.namespace for item in providers.composition.results
    }

    mounted_provider_ids = {
        item.provider_id
        for item in providers.composition.results
        if item.mounted
    }
    local_runtime_tools = _listed_safe_tools(server)
    desktop_commander_tools = (
        _listed_desktop_commander_tools(
            launch=dict(launch),
            provider_args=provider_args,
            environment=environment,
            create_proxy_fn=create_proxy_fn,
            server_name=runtime.server_name,
        )
        if isinstance(server, FastMCPProxy)
        else []
    )
    static_runtime_tools = (
        *local_runtime_tools,
        *desktop_commander_tools,
        *_declared_provider_tools(
            provider_contributions,
            mounted_provider_ids,
        ),
    )
    capabilities = CapabilityRuntimeState.build(
        CapabilityCatalogue(base_contributions, workflow_descriptors()),
        settings,
        runtime_tools_source=lambda: (
            *static_runtime_tools,
            *provider_runtime_tools(
                providers.service,
                providers.composition,
            ),
        ),
        contributions_source=lambda: (
            *static_contributions,
            *current_skill_contributions(),
        ),
        provider_namespaces=namespaces,
    )
    register_capability_tools(
        server,
        capabilities,
        state_root=runtime.state_root,
        quarantine_expired=quarantine.quarantine,
    )
    exposure = ExposurePlanner(capabilities).plan()
    server.add_middleware(ExposureMiddleware(set(exposure.direct_operations)))
    return GatewayComposition(
        server=server,
        capabilities=capabilities,
        exposure=exposure,
        provider_service=providers.service,
        provider_composition=providers.composition,
        projects=projects,
    )


__all__ = ["compose_gateway"]
