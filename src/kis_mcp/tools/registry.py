from __future__ import annotations

from collections.abc import Iterable

from .contracts import ToolDescriptor


class ToolRegistry:
    """Deterministic registry for tool descriptors only."""

    def __init__(self, descriptors: Iterable[ToolDescriptor] = ()) -> None:
        self._tools: dict[str, ToolDescriptor] = {}
        for descriptor in descriptors:
            self.register(descriptor)

    def register(self, descriptor: ToolDescriptor) -> ToolDescriptor:
        if descriptor.tool_id in self._tools:
            raise ValueError(f"Tool is already registered: {descriptor.tool_id}")
        self._tools[descriptor.tool_id] = descriptor
        return descriptor

    def contains(self, tool_id: str) -> bool:
        return tool_id in self._tools

    def get(self, tool_id: str) -> ToolDescriptor:
        try:
            return self._tools[tool_id]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {tool_id}") from exc

    def list(self) -> tuple[ToolDescriptor, ...]:
        return tuple(self._tools[key] for key in sorted(self._tools))

    def __len__(self) -> int:
        return len(self._tools)


__all__ = ["ToolRegistry"]
