from __future__ import annotations

from pathlib import Path, PureWindowsPath

from .contract import StateNamespaceRequest, StateOwnershipClass
from .resolver import StateNamespaceResolver


def resolve_runtime_state_path(
    state_root: str | Path,
    *,
    runtime_instance_id: str,
    state_key: str,
) -> Path:
    """Materialize one canonical runtime namespace under the configured state root."""
    namespace = StateNamespaceResolver().resolve(
        StateNamespaceRequest(
            ownership=StateOwnershipClass.RUNTIME_INSTANCE_SPECIFIC,
            state_key=state_key,
            identities={"runtime_instance_id": runtime_instance_id},
        )
    )
    return Path(state_root).joinpath(*PureWindowsPath(namespace.relative_path).parts)


__all__ = ["resolve_runtime_state_path"]
