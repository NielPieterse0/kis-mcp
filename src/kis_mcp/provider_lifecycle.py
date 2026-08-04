from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path


PROVIDER_STATE_ENV = "KIS_MCP_PROVIDER_STATE_FILE"


def prepare_provider_launch(
    *,
    args: Sequence[object],
    environment: Mapping[object, object],
    provider_state_file: str,
) -> tuple[list[str], dict[str, str]]:
    adapter = Path(__file__).with_name("provider_state_atomic.cjs").resolve()
    if not adapter.is_file():
        raise RuntimeError(f"Provider state adapter is missing: {adapter}")

    prepared_environment = {
        str(key): str(value) for key, value in environment.items()
    }
    prepared_environment[PROVIDER_STATE_ENV] = str(provider_state_file)
    prepared_args = ["--require", str(adapter), *[str(value) for value in args]]
    return prepared_args, prepared_environment
