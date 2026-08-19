from __future__ import annotations

from typing import Any, Mapping, Protocol


class OperationInvoker(Protocol):
    async def read(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]: ...

    async def change(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]: ...

    async def external(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]: ...


class FastMCPInvoker:
    def __init__(self, server: Any) -> None:
        self._server = server

    @staticmethod
    def _structured_payload(operation: str, result: Any) -> dict[str, Any]:
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

    @staticmethod
    def _is_result_budget_envelope(payload: Mapping[str, Any]) -> bool:
        original_chars = payload.get("original_chars")
        max_chars = payload.get("max_chars")
        return (
            payload.get("truncated") is True
            and payload.get("reason") == "RESULT_BUDGET_EXCEEDED"
            and type(original_chars) is int
            and type(max_chars) is int
            and original_chars > max_chars >= 0
            and "preview" in payload
        )

    async def _call(
        self, surface: str, operation: str, arguments: Mapping[str, Any]
    ) -> dict[str, Any]:
        result = await self._server.call_tool(
            surface,
            {"operation": operation, "arguments": dict(arguments)},
        )
        structured = self._structured_payload(operation, result)
        if self._is_result_budget_envelope(structured):
            if structured.get("operation") != operation:
                raise RuntimeError(
                    f"{operation} received mismatched RESULT_BUDGET_EXCEEDED envelope"
                )
            if surface != "execute_read_action":
                raise RuntimeError(
                    f"{operation} returned RESULT_BUDGET_EXCEEDED; refusing mutation replay"
                )
            direct = await self._server.call_tool(
                operation,
                dict(arguments),
                run_middleware=True,
            )
            return self._structured_payload(operation, direct)
        return structured

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
