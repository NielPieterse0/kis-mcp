from __future__ import annotations

from .board import WorkBoardProjectionBridge

_DEFAULT_WORK_BOARD_BRIDGE = WorkBoardProjectionBridge()


def get_work_board_bridge() -> WorkBoardProjectionBridge:
    """Return the process-local derived board bridge; it is not durable authority."""

    return _DEFAULT_WORK_BOARD_BRIDGE


__all__ = ["get_work_board_bridge"]
