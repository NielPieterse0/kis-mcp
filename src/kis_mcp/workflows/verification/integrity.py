from __future__ import annotations

from typing import Protocol


class ExecutableWorkflow(Protocol):
    executable_steps: tuple[str, ...]


def unresolved_executable_steps(
    workflow: ExecutableWorkflow,
    *,
    operation_names: set[str] | frozenset[str],
    workflow_ids: set[str] | frozenset[str],
) -> tuple[str, ...]:
    resolved = set(operation_names) | set(workflow_ids)
    return tuple(step for step in workflow.executable_steps if step not in resolved)


__all__ = ["ExecutableWorkflow", "unresolved_executable_steps"]
