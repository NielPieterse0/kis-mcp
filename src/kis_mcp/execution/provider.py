from __future__ import annotations

from typing import Protocol

from .contracts import ExecutionReadiness, ExecutionRequest, ExecutionResult


class ExecutionProvider(Protocol):
    backend_id: str

    async def readiness(self) -> ExecutionReadiness: ...

    async def execute(self, request: ExecutionRequest) -> ExecutionResult: ...


__all__ = ["ExecutionProvider"]
