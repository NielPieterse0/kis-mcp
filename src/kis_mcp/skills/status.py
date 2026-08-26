from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SkillsRuntimeStatus:
    state: str
    code: str | None = None

    def implementation_value(self) -> str:
        if self.state == "ready":
            return "ready"
        return f"{self.state}:{self.code or 'unknown'}"


def ready_skills_runtime_status() -> SkillsRuntimeStatus:
    return SkillsRuntimeStatus(state="ready")


def degraded_skills_runtime_status(code: str) -> SkillsRuntimeStatus:
    return SkillsRuntimeStatus(state="degraded", code=str(code))


__all__ = [
    "SkillsRuntimeStatus",
    "degraded_skills_runtime_status",
    "ready_skills_runtime_status",
]
