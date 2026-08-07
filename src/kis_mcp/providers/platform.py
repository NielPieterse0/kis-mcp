from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..capabilities.contracts import (
    CapabilityContribution,
    CapabilityDomain,
    ExposureMode,
    ExposurePolicy,
    OperationDescriptor,
    ReadinessSnapshot,
    ReadinessState,
)
from ..capabilities.normalization import default_quality, normalize_effects
from ..config import RuntimeConfig
from .contracts import ProviderDescriptor, ProviderState
from .control_center import register_control_center_provider
from .desktop_commander import register_desktop_commander_provider
from .github import GitHubProviderSettings, register_github_provider
from .github.project_management import GitHubProjectManagementAdapter
from .nvidia import (
    NvidiaSettings,
    disabled_nvidia_settings,
    register_nvidia_provider,
)
from .registry import ProviderRegistry
from .runtime import (
    ProviderMountResult,
    ProviderMountState,
    ProviderRuntimeComposition,
    compose_provider_runtime,
    provider_runtime_status,
)
from .runtime_settings import ProviderRuntimeSettings, load_provider_runtime_settings
from .service import ProviderService


def register_supabase_provider(registry: ProviderRegistry) -> None:
    """Register Supabase lazily so invalid optional config cannot break core startup."""

    try:
        from .supabase import register_provider
    except Exception as exc:
        is_configuration_error = (
            type(exc).__module__ == "kis_mcp.providers.supabase.config"
            and type(exc).__name__ == "SupabaseProviderConfigError"
        )
        if not is_configuration_error:
            raise
        return
    register_provider(registry)


def build_platform_provider_registry(
    *,
    runtime_config: RuntimeConfig | None = None,
    github_settings: GitHubProviderSettings | None = None,
    nvidia_settings: NvidiaSettings | None = None,
    environment: Mapping[str, str] | None = None,
    control_center_status_source=None,
) -> ProviderRegistry:
    """Register approved providers explicitly without building or probing them."""

    registry = ProviderRegistry()
    register_control_center_provider(
        registry, provider_status_source=control_center_status_source
    )
    register_desktop_commander_provider(registry, runtime_config)
    register_github_provider(
        registry,
        settings=github_settings,
        environ=environment,
    )
    register_nvidia_provider(
        registry,
        settings=nvidia_settings or disabled_nvidia_settings(),
        environ=environment,
    )
    register_supabase_provider(registry)
    return registry


def build_platform_provider_service(
    *,
    runtime_config: RuntimeConfig | None = None,
    github_settings: GitHubProviderSettings | None = None,
    nvidia_settings: NvidiaSettings | None = None,
    environment: Mapping[str, str] | None = None,
    control_center_status_source=None,
) -> ProviderService:
    """Build the provider-neutral service over the explicit platform registry."""

    return ProviderService(
        build_platform_provider_registry(
            runtime_config=runtime_config,
            github_settings=github_settings,
            nvidia_settings=nvidia_settings,
            environment=environment,
            control_center_status_source=control_center_status_source,
        )
    )


class _NamespacedProviderToolCaller:
    def __init__(self, server, namespace: str) -> None:
        self.server = server
        self.namespace = namespace.strip("_")

    async def call_tool(self, name: str, arguments: Mapping[str, object]):
        return await self.server.call_tool(
            f"{self.namespace}_{name}",
            dict(arguments),
        )


def build_platform_github_project_backend(
    server,
    service: ProviderService,
    bindings: Mapping[str, object],
):
    if not bindings or not service.registry.contains("github-mcp"):
        raise RuntimeError("github-mcp project management is unavailable")
    descriptor = service.registry.get("github-mcp")
    available_tools = tuple(
        tool_name
        for capability in descriptor.capabilities
        for tool_name in capability.tool_names
        if tool_name in {"projects_get", "projects_list", "projects_write"}
    )
    return GitHubProjectManagementAdapter(
        _NamespacedProviderToolCaller(server, "github"),
        bindings,
        available_tools=available_tools,
    )


def build_platform_nvidia_backend(service: ProviderService, settings: NvidiaSettings):
    if not settings.enabled or not service.registry.contains("nvidia-nim"):
        raise RuntimeError("nvidia-nim is unavailable")
    return service.build("nvidia-nim")

@dataclass(frozen=True, slots=True)
class PlatformProviderRuntime:
    service: ProviderService
    settings: ProviderRuntimeSettings
    composition: ProviderRuntimeComposition


def compose_platform_providers(
    server,
    *,
    runtime_config: RuntimeConfig,
    nvidia_settings: NvidiaSettings,
    provider_service: ProviderService | None = None,
    provider_runtime_settings: ProviderRuntimeSettings | None = None,
    environment: Mapping[str, str] | None = None,
) -> PlatformProviderRuntime:
    holder: dict[str, object] = {}

    def current_status():
        active_service = holder.get("service")
        active_composition = holder.get("composition")
        if not isinstance(active_service, ProviderService) or not isinstance(
            active_composition, ProviderRuntimeComposition
        ):
            return {"external_providers": []}
        return provider_runtime_status(active_service, active_composition)

    service = provider_service or build_platform_provider_service(
        runtime_config=runtime_config,
        nvidia_settings=nvidia_settings,
        environment=environment,
        control_center_status_source=current_status,
    )
    holder["service"] = service
    settings = provider_runtime_settings or load_provider_runtime_settings()
    composition = compose_provider_runtime(server, service, settings)
    holder["composition"] = composition
    return PlatformProviderRuntime(service=service, settings=settings, composition=composition)

def _mount_readiness(result: ProviderMountResult) -> ReadinessSnapshot | None:
    state = {
        ProviderMountState.DISABLED: ReadinessState.DISABLED,
        ProviderMountState.UNREGISTERED: ReadinessState.UNAVAILABLE,
        ProviderMountState.BUILD_FAILED: ReadinessState.BUILD_FAILED,
        ProviderMountState.INVALID_BUILDER_RESULT: ReadinessState.BUILD_FAILED,
        ProviderMountState.MOUNT_FAILED: ReadinessState.MOUNT_FAILED,
        ProviderMountState.MOUNTED: ReadinessState.READY,
    }[result.state]
    if result.state is ProviderMountState.MOUNTED:
        return None
    details = {"namespace": result.namespace}
    if result.error_type is not None:
        details["error_type"] = result.error_type
    return ReadinessSnapshot(
        contribution_id=f"provider.{result.provider_id}",
        state=state,
        summary=f"Provider runtime state is {result.state.value}.",
        details=details,
    )


def _descriptor_readiness(descriptor: ProviderDescriptor) -> ReadinessSnapshot:
    raw = descriptor.readiness_probe()
    details = dict(raw.details)
    user_status = details.get("user_status")
    user_state = ""
    if isinstance(user_status, Mapping):
        user_state = str(user_status.get("state", "")).casefold()
    if "authentication_required" in user_state:
        state = ReadinessState.AUTHENTICATION_REQUIRED
    elif "initialization_required" in user_state or details.get("upstream_ready") is False:
        state = ReadinessState.UNAVAILABLE
    else:
        state = {
            ProviderState.READY: ReadinessState.READY,
            ProviderState.DEGRADED: ReadinessState.DEGRADED,
            ProviderState.DISABLED: ReadinessState.DISABLED,
            ProviderState.UNAVAILABLE: ReadinessState.UNAVAILABLE,
        }[raw.state]
    return ReadinessSnapshot(
        contribution_id=f"provider.{descriptor.provider_id}",
        state=state,
        summary=raw.summary,
        details=details,
    )


def provider_capability_contributions(
    service: ProviderService,
    composition: ProviderRuntimeComposition,
) -> tuple[CapabilityContribution, ...]:
    mount_by_id = {item.provider_id: item for item in composition.results}
    contributions: list[CapabilityContribution] = []
    for descriptor in service.registry.list():
        mount = mount_by_id.get(descriptor.provider_id)
        operations: list[OperationDescriptor] = []
        all_effects: list[str] = []
        for capability in descriptor.capabilities:
            all_effects.extend(capability.effects)
            for tool_name in capability.tool_names:
                exposed_name = tool_name
                if mount is not None and mount.namespace and not tool_name.startswith(f"{mount.namespace}_"):
                    exposed_name = f"{mount.namespace}_{tool_name}"
                effects = normalize_effects(capability.effects)
                operations.append(
                    OperationDescriptor(
                        operation_id=f"provider.{descriptor.provider_id}.{tool_name}",
                        name=exposed_name,
                        description=capability.description,
                        capabilities=(capability.capability_id,),
                        effects=effects,
                        dependencies=(),
                        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=60),
                        quality=default_quality(context_cost=45, workflow_integration=75),
                        authentication_preflight=("auth" in tool_name or "status" in tool_name or "preflight" in tool_name),
                        approval_required=("merge" in tool_name or "delete" in tool_name),
                        enabled=descriptor.enabled,
                    )
                )
        contribution_id = f"provider.{descriptor.provider_id}"

        def readiness_probe(
            descriptor: ProviderDescriptor = descriptor,
            mount: ProviderMountResult | None = mount,
        ) -> ReadinessSnapshot:
            if mount is not None:
                mount_snapshot = _mount_readiness(mount)
                if mount_snapshot is not None:
                    return mount_snapshot
            return _descriptor_readiness(descriptor)

        contributions.append(
            CapabilityContribution(
                contribution_id=contribution_id,
                domain=CapabilityDomain.PROVIDER,
                category=descriptor.provider_kind.value.replace("_", "-"),
                capabilities=tuple(item.capability_id for item in descriptor.capabilities),
                operations=tuple(operations),
                dependencies=(),
                effects=normalize_effects(all_effects),
                readiness_probe=readiness_probe,
                exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=55),
                quality=default_quality(context_cost=40, workflow_integration=75),
            )
        )
    return tuple(contributions)


__all__ = [
    "PlatformProviderRuntime",
    "ProviderRuntimeSettings",
    "ProviderService",
    "build_platform_github_project_backend",
    "build_platform_nvidia_backend",
    "build_platform_provider_registry",
    "build_platform_provider_service",
    "compose_platform_providers",
    "provider_capability_contributions",
]
