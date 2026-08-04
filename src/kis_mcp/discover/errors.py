from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DiscoverError(ValueError):
    code: str
    message: str
    reason: str
    field: str | None = None
    accepted: str | None = None
    corrective_actions: tuple[str, ...] = ()
    retryable: bool = False

    def __post_init__(self) -> None:
        ValueError.__init__(self, self.message)
        if not self.code.startswith("DISCOVER_"):
            raise ValueError("Discover error code must start with DISCOVER_")
        if not self.message.strip() or not self.reason.strip():
            raise ValueError("Discover error message and reason must be non-empty")
        if any(not action.strip() for action in self.corrective_actions):
            raise ValueError("Discover corrective actions must be non-empty")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "reason": self.reason,
            "field": self.field,
            "accepted": self.accepted,
            "corrective_actions": list(self.corrective_actions),
            "retryable": self.retryable,
        }


__all__ = ["DiscoverError"]
