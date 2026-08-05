from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .contracts import (
    PUBLIC_SCHEMA_VERSION,
    ToolDescriptor,
    ToolReadiness,
    ToolState,
    _require_enum,
)


@dataclass(frozen=True, slots=True)
class ToolHealthSummary:
    state: ToolState
    tools: tuple[ToolReadiness, ...]
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("tool health summary schema_version must be 1")
        _require_enum(self.state, ToolState, "state")
        if any(
            not isinstance(item, ToolReadiness) for item in self.tools
        ):
            raise ValueError("tools must contain ToolReadiness values")
        tool_ids = [item.tool_id for item in self.tools]
        if len(set(tool_ids)) != len(tool_ids):
            raise ValueError("tools must contain unique tool_id values")
        object.__setattr__(
            self,
            "tools",
            tuple(sorted(self.tools, key=lambda item: item.tool_id)),
        )

    @property
    def ready_count(self) -> int:
        return self._count(ToolState.READY)

    @property
    def degraded_count(self) -> int:
        return self._count(ToolState.DEGRADED)

    @property
    def disabled_count(self) -> int:
        return self._count(ToolState.DISABLED)

    @property
    def unavailable_count(self) -> int:
        return self._count(ToolState.UNAVAILABLE)

    def _count(self, state: ToolState) -> int:
        return sum(item.state is state for item in self.tools)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "state": self.state.value,
            "ready_count": self.ready_count,
            "degraded_count": self.degraded_count,
            "disabled_count": self.disabled_count,
            "unavailable_count": self.unavailable_count,
            "tools": [item.to_json_dict() for item in self.tools],
        }


def _probe_tool(descriptor: ToolDescriptor) -> ToolReadiness:
    if not descriptor.enabled:
        return ToolReadiness(
            tool_id=descriptor.tool_id,
            state=ToolState.DISABLED,
            summary="Tool is disabled.",
        )

    try:
        readiness = descriptor.readiness_probe()
    except Exception as exc:
        return ToolReadiness(
            tool_id=descriptor.tool_id,
            state=ToolState.UNAVAILABLE,
            summary="Tool readiness probe failed.",
            details={"error_type": type(exc).__name__},
        )

    if not isinstance(readiness, ToolReadiness):
        return ToolReadiness(
            tool_id=descriptor.tool_id,
            state=ToolState.UNAVAILABLE,
            summary="Tool readiness probe returned an invalid result.",
            details={"reported_type": type(readiness).__name__},
        )

    if readiness.tool_id != descriptor.tool_id:
        return ToolReadiness(
            tool_id=descriptor.tool_id,
            state=ToolState.UNAVAILABLE,
            summary="Tool readiness probe returned mismatched identity.",
            details={"reported_tool_id": readiness.tool_id},
        )
    return readiness


def _aggregate_state(readiness: tuple[ToolReadiness, ...]) -> ToolState:
    if not readiness:
        return ToolState.UNAVAILABLE
    active = tuple(item for item in readiness if item.state is not ToolState.DISABLED)
    if not active:
        return ToolState.DISABLED
    if all(item.state is ToolState.UNAVAILABLE for item in active):
        return ToolState.UNAVAILABLE
    if any(
        item.state in {ToolState.DEGRADED, ToolState.UNAVAILABLE}
        for item in active
    ):
        return ToolState.DEGRADED
    return ToolState.READY


def aggregate_tool_health(
    descriptors: Iterable[ToolDescriptor],
) -> ToolHealthSummary:
    readiness = tuple(
        _probe_tool(descriptor)
        for descriptor in sorted(descriptors, key=lambda item: item.tool_id)
    )
    return ToolHealthSummary(
        state=_aggregate_state(readiness),
        tools=readiness,
    )


__all__ = ["ToolHealthSummary", "aggregate_tool_health"]
