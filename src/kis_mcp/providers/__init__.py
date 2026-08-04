"""Provider-neutral contracts and orchestration for kis-mcp providers."""

from .catalogue import ProviderCatalogue, ProviderCatalogueEntry
from .contracts import (
    PUBLIC_SCHEMA_VERSION,
    ProviderBoundary,
    ProviderBuilder,
    ProviderCapability,
    ProviderDescriptor,
    ProviderKind,
    ProviderReadiness,
    ProviderReadinessProbe,
    ProviderState,
)
from .health import ProviderHealthSummary, aggregate_provider_health
from .registry import ProviderRegistry
from .service import ProviderService

__all__ = [
    "PUBLIC_SCHEMA_VERSION",
    "ProviderBoundary",
    "ProviderBuilder",
    "ProviderCapability",
    "ProviderCatalogue",
    "ProviderCatalogueEntry",
    "ProviderDescriptor",
    "ProviderHealthSummary",
    "ProviderKind",
    "ProviderReadiness",
    "ProviderReadinessProbe",
    "ProviderRegistry",
    "ProviderService",
    "ProviderState",
    "aggregate_provider_health",
]
