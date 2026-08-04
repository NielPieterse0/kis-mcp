from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .models import InvocationEffects, PolicyDecision


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Provider-surface facts required by the enforcement boundary."""

    network_only_tools: frozenset[str]
    direct_delete_tools: frozenset[str]
    unexposed_tool_arguments: Mapping[str, frozenset[str]]
    unexposed_config_keys: frozenset[str]
    configuration_tool_name: str | None


@runtime_checkable
class ProviderEffectResolver(Protocol):
    @property
    def capabilities(self) -> ProviderCapabilities: ...

    def resolve(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None,
    ) -> InvocationEffects: ...


@runtime_checkable
class PolicyEvaluator(Protocol):
    def evaluate(self, effects: InvocationEffects) -> PolicyDecision: ...


@runtime_checkable
class QuarantineRecordView(Protocol):
    operation_id: str
    original_path: str
    payload_path: str
    item_type: str
    quarantined_at: str
    restored_at: str | None


@runtime_checkable
class QuarantinePort(Protocol):
    def quarantine(self, path: str) -> QuarantineRecordView: ...

    def restore(self, operation_id: str) -> QuarantineRecordView: ...

    def list_records(self, *, limit: int = 50) -> list[QuarantineRecordView]: ...
