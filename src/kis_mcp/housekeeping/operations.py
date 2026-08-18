from __future__ import annotations

from typing import Any, Mapping, Protocol


class OperationInvoker(Protocol):
    async def read(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]: ...

    async def change(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]: ...

    async def external(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]: ...


class FastMCPInvoker:
    def __init__(self, server: Any) -> None:
        self._server = server

    async def _call(
        self, surface: str, operation: str, arguments: Mapping[str, Any]
    ) -> dict[str, Any]:
        result = await self._server.call_tool(
            surface,
            {"operation": operation, "arguments": dict(arguments)},
        )
        if getattr(result, "is_error", False):
            detail = "; ".join(
                str(getattr(item, "text", ""))
                for item in getattr(result, "content", ())
            )
            raise RuntimeError(f"{operation} failed: {detail}")
        structured = getattr(result, "structured_content", None)
        if not isinstance(structured, dict):
            raise RuntimeError(f"{operation} returned no structured content")
        return dict(structured)

    async def read(
        self, operation: str, arguments: Mapping[str, Any]
    ) -> dict[str, Any]:
        return await self._call("execute_read_action", operation, arguments)

    async def change(
        self, operation: str, arguments: Mapping[str, Any]
    ) -> dict[str, Any]:
        return await self._call("execute_change_action", operation, arguments)

    async def external(
        self, operation: str, arguments: Mapping[str, Any]
    ) -> dict[str, Any]:
        return await self._call("execute_external_action", operation, arguments)


__all__ = ["FastMCPInvoker", "OperationInvoker"]
