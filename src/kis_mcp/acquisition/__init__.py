"""Registered external-acquisition authorization and provider routing."""

from .service import RegisteredAcquisitionService, execute_registered_acquisition_operation
from .settings import ExternalAcquisitionSettings, load_external_acquisition_settings

__all__ = [
    "ExternalAcquisitionSettings",
    "RegisteredAcquisitionService",
    "execute_registered_acquisition_operation",
    "load_external_acquisition_settings",
]
