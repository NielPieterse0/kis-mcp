from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DecisionKind(StrEnum):
    ALLOW = "allow"
    BLOCK = "block"
    QUARANTINE = "quarantine"


@dataclass(frozen=True, slots=True)
class InvocationEffects:
    """Provider-neutral effects resolved from one concrete invocation.

    ``write_paths`` may write through the final path target and therefore require
    full effective-path resolution. ``entry_paths`` mutate directory entries
    (for example, move sources) and resolve only existing ancestors. Delete
    intent remains separate because it must be transformed to quarantine.
    """

    write_paths: tuple[str, ...] = ()
    entry_paths: tuple[str, ...] = ()
    delete_paths: tuple[str, ...] = ()
    unresolved_delete: bool = False
    external_network: bool = False

    @property
    def mutated_paths(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys((*self.write_paths, *self.entry_paths, *self.delete_paths))
        )


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    kind: DecisionKind
    code: str
    message: str
    rule_id: str | None = None
    paths: tuple[str, ...] = field(default_factory=tuple)

    @property
    def allowed(self) -> bool:
        return self.kind is DecisionKind.ALLOW
