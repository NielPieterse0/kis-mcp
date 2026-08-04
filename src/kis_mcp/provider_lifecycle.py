from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path


PROVIDER_STATE_ENV = "KIS_MCP_PROVIDER_STATE_FILE"
PROVIDER_STARTUP_COMPAT_ENV = "KIS_MCP_PROVIDER_STARTUP_COMPAT"
PROVIDER_FLAG_URL_ENV = "KIS_MCP_PROVIDER_FLAG_URL"


def prepare_provider_launch(
    *,
    args: Sequence[object],
    environment: Mapping[object, object],
    provider_state_file: str,
) -> tuple[list[str], dict[str, str]]:
    atomic_adapter = Path(__file__).with_name("provider_state_atomic.cjs").resolve()
    startup_adapter = Path(__file__).with_name("provider_startup_compat.cjs").resolve()
    for name, adapter in (
        ("Provider state", atomic_adapter),
        ("Provider startup compatibility", startup_adapter),
    ):
        if not adapter.is_file():
            raise RuntimeError(f"{name} adapter is missing: {adapter}")

    prepared_environment = {
        str(key): str(value) for key, value in environment.items()
    }
    prepared_environment[PROVIDER_STATE_ENV] = str(provider_state_file)
    prepared_environment[PROVIDER_STARTUP_COMPAT_ENV] = "1"
    prepared_environment[PROVIDER_FLAG_URL_ENV] = prepared_environment.get(
        "DC_FLAG_URL", ""
    )
    prepared_args = [
        "--require",
        str(atomic_adapter),
        "--require",
        str(startup_adapter),
        *[str(value) for value in args],
    ]
    return prepared_args, prepared_environment
