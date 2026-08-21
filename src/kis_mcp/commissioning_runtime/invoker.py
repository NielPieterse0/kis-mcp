from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from fastmcp.exceptions import FastMCPError


def _budget_envelope(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    original_chars = value.get("original_chars")
    max_chars = value.get("max_chars")
    return (
        value.get("truncated") is True
        and value.get("reason") == "RESULT_BUDGET_EXCEEDED"
        and type(original_chars) is int
        and type(max_chars) is int
        and original_chars > max_chars >= 0
        and "preview" in value
    )


def _json_text(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}


def _resource_text(resource: Any) -> str:
    text = getattr(resource, "text", None)
    if isinstance(text, str):
        return text
    raise RuntimeError("provider resource did not contain bounded text content")


def _content_items(result: Any) -> tuple[Any, ...]:
    content = getattr(result, "content", ())
    if not isinstance(content, Sequence) or isinstance(content, (str, bytes, bytearray)):
        raise TypeError("provider result content is invalid")
    return tuple(content)


def _error_detail(result: Any) -> str:
    details = [
        str(text)
        for item in _content_items(result)
        if isinstance((text := getattr(item, "text", None)), str) and text
    ]
    return "; ".join(details) or "provider operation failed"


class CommissioningFastMCPInvoker:
    def __init__(self, server: Any) -> None:
        self._server = server

    async def _linked_resource(self, item: Any) -> dict[str, str]:
        uri = getattr(item, "uri", None)
        if uri is None:
            raise RuntimeError("provider resource link has no URI")
        try:
            result = await self._server.read_resource(str(uri))
        except FastMCPError as exc:
            raise RuntimeError("provider resource read failed") from exc
        contents = getattr(result, "contents", None)
        if not isinstance(contents, Sequence) or isinstance(
            contents, (str, bytes, bytearray)
        ):
            raise TypeError("provider resource read returned invalid contents")
        if len(contents) != 1:
            raise RuntimeError("provider resource read must return exactly one content item")
        return {"content": _resource_text(contents[0])}

    async def _payload(self, operation: str, result: Any) -> Any:
        if getattr(result, "is_error", False):
            raise RuntimeError(f"{operation} failed: {_error_detail(result)}")
        structured = getattr(result, "structured_content", None)
        if structured is not None:
            if _budget_envelope(structured):
                raise RuntimeError(
                    f"{operation} returned RESULT_BUDGET_EXCEEDED; refusing replay"
                )
            if (
                isinstance(structured, Mapping)
                and set(structured) == {"result"}
                and isinstance(structured.get("result"), list)
            ):
                return structured["result"]
            return structured

        content = _content_items(result)
        for item in content:
            if getattr(item, "type", None) == "resource_link":
                return await self._linked_resource(item)
        for item in content:
            if getattr(item, "type", None) == "resource":
                resource = getattr(item, "resource", None)
                return {"content": _resource_text(resource)}
        if len(content) == 1:
            text = getattr(content[0], "text", None)
            if isinstance(text, str):
                payload = _json_text(text)
                if _budget_envelope(payload):
                    raise RuntimeError(
                        f"{operation} returned RESULT_BUDGET_EXCEEDED; refusing replay"
                    )
                return payload
        raise RuntimeError(f"{operation} returned no supported bounded result")

    async def _dispatch(
        self,
        control_tool: str,
        operation: str,
        arguments: dict[str, Any],
    ) -> Any:
        try:
            result = await self._server.call_tool(
                control_tool,
                {"operation": operation, "arguments": dict(arguments)},
            )
        except FastMCPError as exc:
            raise RuntimeError(f"{operation} provider call failed") from exc
        return await self._payload(operation, result)

    async def external(self, operation: str, arguments: dict[str, Any]) -> Any:
        return await self._dispatch("execute_external_action", operation, arguments)

    async def read(self, operation: str, arguments: dict[str, Any]) -> Any:
        return await self._dispatch("execute_read_action", operation, arguments)

    async def change(self, operation: str, arguments: dict[str, Any]) -> Any:
        return await self._dispatch("execute_change_action", operation, arguments)


__all__ = ["CommissioningFastMCPInvoker"]
