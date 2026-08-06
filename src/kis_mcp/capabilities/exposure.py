from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext

from .contracts import ReadinessState
from .eligibility import evaluate_eligibility
from .runtime import CapabilityRuntimeState


@dataclass(frozen=True, slots=True)
class ExposurePlan:
    direct_operations: tuple[str, ...]
    discoverable_operations: tuple[str, ...]
    status_only_operations: tuple[str, ...]

    def to_json_dict(self) -> dict[str, object]:
        return {
            "direct_operations": list(self.direct_operations),
            "discoverable_operations": list(self.discoverable_operations),
            "status_only_operations": list(self.status_only_operations),
        }


class ExposurePlanner:
    def __init__(self, runtime: CapabilityRuntimeState) -> None:
        self.runtime = runtime

    def plan(
        self,
        *,
        explicit_operations: set[str] | frozenset[str] = frozenset(),
    ) -> ExposurePlan:
        direct: set[str] = set()
        discoverable: set[str] = set()
        status_only: set[str] = set()
        explicit = set(explicit_operations)
        configured_direct = set(self.runtime.settings.direct_operations)

        for operation in self.runtime.catalogue.operations:
            readiness = self.runtime.readiness_for(operation)
            decision = evaluate_eligibility(
                operation,
                readiness=readiness,
                available_capabilities=self.runtime.available_capabilities,
                requested_effects=frozenset(),
                credentials_available=frozenset(),
            )
            if not decision.eligible:
                if readiness.state in {
                    ReadinessState.AUTHENTICATION_REQUIRED,
                    ReadinessState.UNAVAILABLE,
                    ReadinessState.DISABLED,
                    ReadinessState.BUILD_FAILED,
                    ReadinessState.MOUNT_FAILED,
                }:
                    status_only.add(operation.name)
                continue

            explicitly_requested = (
                operation.name in explicit or operation.operation_id in explicit
            )
            if operation.name in configured_direct or (
                explicitly_requested and operation.exposure.explicit_request_allowed
            ):
                direct.add(operation.name)
            else:
                discoverable.add(operation.name)

        if len(direct) > self.runtime.settings.direct_profile_max:
            priorities = {
                operation.name: operation.exposure.priority
                for operation in self.runtime.catalogue.operations
            }
            direct = set(
                sorted(direct, key=lambda name: (-priorities.get(name, 0), name))[
                    : self.runtime.settings.direct_profile_max
                ]
            )

        return ExposurePlan(
            direct_operations=tuple(sorted(direct)),
            discoverable_operations=tuple(sorted(discoverable - direct)),
            status_only_operations=tuple(sorted(status_only)),
        )


class ExposureMiddleware(Middleware):
    """Filter tools/list only; do not disable valid server-side operations."""

    def __init__(self, direct_operations: set[str] | frozenset[str]) -> None:
        self.direct_operations = frozenset(direct_operations)

    async def on_list_tools(
        self,
        context: MiddlewareContext,
        call_next: Any,
    ) -> list[Any]:
        tools = await call_next(context)
        return [
            tool
            for tool in tools
            if str(getattr(tool, "name", "")) in self.direct_operations
        ]


__all__ = ["ExposureMiddleware", "ExposurePlan", "ExposurePlanner"]
