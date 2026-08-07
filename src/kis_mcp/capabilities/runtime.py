from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from .catalogue import CapabilityCatalogue
from .contracts import OperationDescriptor, ReadinessSnapshot
from .readiness import available_capabilities, evaluate_readiness
from .resolver import CapabilityResolver
from .settings import CapabilitySettings
from .surface import augment_with_runtime_surface


RuntimeToolsSource = Callable[[], Sequence[Any]]


@dataclass(frozen=True, slots=True)
class CapabilityRuntimeState:
    """Instance-scoped capability state with live provider readiness/tool refresh."""

    base_catalogue: CapabilityCatalogue
    settings: CapabilitySettings
    runtime_tools_source: RuntimeToolsSource | None = None
    provider_namespaces: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({})
    )

    @classmethod
    def build(
        cls,
        catalogue: CapabilityCatalogue,
        settings: CapabilitySettings,
        *,
        runtime_tools_source: RuntimeToolsSource | None = None,
        provider_namespaces: Mapping[str, str] | None = None,
    ) -> "CapabilityRuntimeState":
        return cls(
            base_catalogue=catalogue,
            settings=settings,
            runtime_tools_source=runtime_tools_source,
            provider_namespaces=MappingProxyType(dict(provider_namespaces or {})),
        )

    @property
    def catalogue(self) -> CapabilityCatalogue:
        if self.runtime_tools_source is None:
            return self.base_catalogue
        contributions = augment_with_runtime_surface(
            self.base_catalogue.contributions,
            tuple(self.runtime_tools_source()),
            dict(self.provider_namespaces),
        )
        return CapabilityCatalogue(contributions, self.base_catalogue.workflows)

    @property
    def readiness(self) -> Mapping[str, ReadinessSnapshot]:
        catalogue = self.catalogue
        return MappingProxyType(dict(evaluate_readiness(catalogue.contributions)))

    @property
    def resolver(self) -> CapabilityResolver:
        return CapabilityResolver(self.catalogue, self.settings)

    @property
    def available_capabilities(self) -> frozenset[str]:
        catalogue = self.catalogue
        readiness = evaluate_readiness(catalogue.contributions)
        return available_capabilities(catalogue.contributions, readiness)

    def operation(self, operation_id_or_name: str) -> OperationDescriptor:
        return self.catalogue.operation(operation_id_or_name)

    def readiness_for(self, operation: OperationDescriptor) -> ReadinessSnapshot:
        catalogue = self.catalogue
        contribution = catalogue.contribution_for(operation)
        return evaluate_readiness(catalogue.contributions)[contribution.contribution_id]


__all__ = ["CapabilityRuntimeState", "RuntimeToolsSource"]
