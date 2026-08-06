from __future__ import annotations

from dataclasses import dataclass

from fastmcp import FastMCP

from ..capabilities.exposure import ExposurePlan
from ..capabilities.runtime import CapabilityRuntimeState
from ..providers.runtime import ProviderRuntimeComposition
from ..providers.service import ProviderService


@dataclass(frozen=True, slots=True)
class GatewayComposition:
    server: FastMCP
    capabilities: CapabilityRuntimeState
    exposure: ExposurePlan
    provider_service: ProviderService
    provider_composition: ProviderRuntimeComposition


__all__ = ["GatewayComposition"]
