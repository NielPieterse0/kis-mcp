from __future__ import annotations

import os
from collections.abc import Mapping
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastmcp.server.providers import Provider

from .service import HousekeepingRuntimeService

_INSTANCE_MAP = {
    "operation": "kis-op",
    "op": "kis-op",
    "kis-op": "kis-op",
    "development": "kis-dev",
    "dev": "kis-dev",
    "kis-dev": "kis-dev",
}


def normalized_runtime_instance(
    environment: Mapping[str, str] | None = None,
) -> str:
    source = os.environ if environment is None else environment
    selected = str(source.get("KIS_MCP_RUNTIME_INSTANCE", "stdio")).strip().casefold()
    if not selected:
        selected = "stdio"
    return _INSTANCE_MAP.get(selected, selected)


class HousekeepingLifecycleProvider(Provider):
    def __init__(self, service: HousekeepingRuntimeService) -> None:
        super().__init__()
        self.service = service

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        await self.service.start()
        try:
            yield
        finally:
            await self.service.stop()


__all__ = ["HousekeepingLifecycleProvider", "normalized_runtime_instance"]
