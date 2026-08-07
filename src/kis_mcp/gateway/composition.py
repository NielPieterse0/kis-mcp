from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from typing import Any

from fastmcp import FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.server.providers.proxy import ProxyClient

from ..capabilities.catalogue import CapabilityCatalogue
from ..capabilities.exposure import ExposureMiddleware, ExposurePlanner
from ..capabilities.runtime import CapabilityRuntimeState
from ..capabilities.settings import load_capability_settings
from ..capabilities.surface import (
    augment_with_runtime_surface,
    capability_control_contribution,
)
from ..capabilities.tools import register_capability_tools
from ..config import RuntimeConfig, load_runtime_config
from ..desktop_commander import DesktopCommanderEffectResolver
from ..discover.platform import (
    discover_capability_contributions,
    register_platform_discover,
)
from ..middleware import ThreeRuleMiddleware
from ..policy import ThreeRulePolicy
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
from ..skills.platform import register_platform_skills, skill_capability_contributions
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


def _listed_tools(server: FastMCP) -> list[Any]:
    return list(asyncio.run(server.list_tools()))


def _listed_local_tools(server: FastMCP) -> list[Any]:
    return list(asyncio.run(server.local_provider.list_tools()))


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

    # Capture the existing Work backend before mounting external providers. This
    # may inspect Desktop Commander, but cannot create a disposable GitHub MCP
    # subprocess because GitHub has not been mounted yet.
    core_runtime_tools = _listed_tools(server)

    register_platform_discover(server, runtime)
    providers = compose_platform_providers(
        server,
        runtime_config=runtime,
        nvidia_settings=agent_settings.nvidia,
        provider_service=provider_service,
        provider_runtime_settings=provider_runtime_settings,
        environment=os.environ,
    )

    quarantine = QuarantineService(
        project_boundary=runtime.project_boundary,
        quarantine_root=runtime.quarantine_root,
    )
    register_gateway_operations(
        server,
        runtime=runtime,
        launch=dict(launch),
        quarantine=quarantine,
        provider_service=providers.service,
        provider_composition=providers.composition,
    )
    register_platform_workflows(
        server,
        runtime,
        agent_settings,
        providers.service,
    )

    resolver = DesktopCommanderEffectResolver(
        project_boundary=runtime.project_boundary,
        provider_state_file=runtime.provider_state_file,
    )
    policy = ThreeRulePolicy(
        project_boundary=runtime.project_boundary,
        quarantine_root=runtime.quarantine_root,
    )
    server.add_middleware(
        ThreeRuleMiddleware(
            resolver=resolver,
            policy=policy,
            quarantine_paths=lambda paths: quarantine_many_payloads(quarantine, paths),
        )
    )
    _, skill_cards = register_platform_skills(server)

    settings = load_capability_settings()
    base_contributions = (
        *provider_capability_contributions(providers.service, providers.composition),
        *tool_capability_contributions(build_platform_tool_registry()),
        *discover_capability_contributions(),
        *skill_capability_contributions(skill_cards, settings),
        capability_control_contribution(),
    )
    namespaces = {
        item.provider_id: item.namespace for item in providers.composition.results
    }
    static_runtime_tools = (
        *core_runtime_tools,
        *_listed_local_tools(server),
    )
    contributions = augment_with_runtime_surface(
        base_contributions,
        static_runtime_tools,
        namespaces,
    )
    capabilities = CapabilityRuntimeState.build(
        CapabilityCatalogue(contributions, workflow_descriptors()),
        settings,
        runtime_tools_source=lambda: provider_runtime_tools(
            providers.service,
            providers.composition,
        ),
        provider_namespaces=namespaces,
    )
    register_capability_tools(server, capabilities)
    exposure = ExposurePlanner(capabilities).plan()
    server.add_middleware(ExposureMiddleware(set(exposure.direct_operations)))
    return GatewayComposition(
        server=server,
        capabilities=capabilities,
        exposure=exposure,
        provider_service=providers.service,
        provider_composition=providers.composition,
    )


__all__ = ["compose_gateway"]
