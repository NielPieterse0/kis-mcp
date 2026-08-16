"""Composed kis-mcp workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .platform import workflow_descriptors as workflow_descriptors

__all__ = [
    "workflow_descriptors",
]


def __getattr__(name: str) -> Any:
    if name == "workflow_descriptors":
        from .platform import workflow_descriptors

        return workflow_descriptors
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
