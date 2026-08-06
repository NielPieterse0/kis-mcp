from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .catalogue import CapabilityCatalogue
from .contracts import OperationDescriptor, ReadinessSnapshot
from .readiness import evaluate_readiness
from .resolver import CapabilityResolver
from .settings import CapabilitySettings


@dataclass(frozen=True, slots=True)
class CapabilityRuntimeState:
    """Instance-scoped catalogue, readiness, and resolver state."""

    catalogue: CapabilityCatalogue
    settings: CapabilitySettings
    readiness: Mapping[str, ReadinessSnapshot]
    resolver: CapabilityResolver

    @classmethod
    def build(
        cls,
        catalogue: CapabilityCatalogue,
        settings: CapabilitySettings,
    ) -> "CapabilityRuntimeState":
        readiness = evaluate_readiness(catalogue.contributions)
        resolver = CapabilityResolver(catalogue, settings)
        return cls(
            catalogue=catalogue,
            settings=settings,
            readiness=MappingProxyType(dict(readiness)),
            resolver=resolver,
        )

    @property
    def available_capabilities(self) -> frozenset[str]:
        return frozenset(
            capability
            for contribution in self.catalogue.contributions
            if self.readiness[contribution.contribution_id].operational
            and (
                not contribution.operations
                or any(operation.enabled for operation in contribution.operations)
            )
            for capability in contribution.capabilities
        )

    def operation(self, operation_id_or_name: str) -> OperationDescriptor:
        return self.catalogue.operation(operation_id_or_name)

    def readiness_for(self, operation: OperationDescriptor) -> ReadinessSnapshot:
        contribution = self.catalogue.contribution_for(operation)
        return self.readiness[contribution.contribution_id]


__all__ = ["CapabilityRuntimeState"]
