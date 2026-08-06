from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from .contracts import CapabilityContribution, ReadinessSnapshot, ReadinessState


def evaluate_readiness(
    contributions: Iterable[CapabilityContribution],
) -> Mapping[str, ReadinessSnapshot]:
    snapshots: dict[str, ReadinessSnapshot] = {}
    for contribution in sorted(contributions, key=lambda item: item.contribution_id):
        try:
            snapshot = contribution.readiness_probe()
            if not isinstance(snapshot, ReadinessSnapshot):
                raise TypeError("probe returned invalid result")
            if snapshot.contribution_id != contribution.contribution_id:
                raise ValueError("probe contribution_id mismatch")
        except Exception as exc:
            snapshot = ReadinessSnapshot(
                contribution_id=contribution.contribution_id,
                state=ReadinessState.UNAVAILABLE,
                summary="readiness probe failed",
                details={"error_type": type(exc).__name__},
            )
        snapshots[contribution.contribution_id] = snapshot
    return MappingProxyType(snapshots)


__all__ = ["evaluate_readiness"]
