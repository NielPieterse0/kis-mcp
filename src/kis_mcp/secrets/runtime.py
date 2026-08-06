from __future__ import annotations

from threading import RLock

from .service import SecretsService


_ACTIVE_SERVICE: SecretsService | None = None
_ACTIVE_LOCK = RLock()


def set_active_secrets_service(service: SecretsService) -> None:
    global _ACTIVE_SERVICE
    with _ACTIVE_LOCK:
        if _ACTIVE_SERVICE is not None and _ACTIVE_SERVICE is not service:
            _ACTIVE_SERVICE.lock()
        _ACTIVE_SERVICE = service


def get_active_secrets_service() -> SecretsService:
    with _ACTIVE_LOCK:
        if _ACTIVE_SERVICE is None:
            raise RuntimeError("KIS_MCP_SECRET_SERVICE_NOT_INITIALIZED")
        return _ACTIVE_SERVICE


def clear_active_secrets_service() -> None:
    global _ACTIVE_SERVICE
    with _ACTIVE_LOCK:
        if _ACTIVE_SERVICE is not None:
            _ACTIVE_SERVICE.lock()
        _ACTIVE_SERVICE = None
