"""KIS Control Center provider registration."""

from .provider import (
    ProviderStatusSource,
    control_center_provider_descriptor,
    register_control_center_provider,
)

__all__ = [
    "ProviderStatusSource",
    "control_center_provider_descriptor",
    "register_control_center_provider",
]
