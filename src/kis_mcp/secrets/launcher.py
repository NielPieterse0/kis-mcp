from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from typing import Any

from .cli import BOOTSTRAP_ENVIRONMENT, build_service, unlock_service
from .errors import SecretsError
from .runtime import clear_active_secrets_service, set_active_secrets_service


PIPE_HANDLE_ENVIRONMENT = "KIS_MCP_SECRET_INPUT_PIPE_HANDLE"
_MAX_PIPE_INPUT_BYTES = 64 * 1024


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kis-mcp-secrets-launcher")
    parser.add_argument("--runtime", choices=("stdio", "remote"), default="stdio")
    parser.add_argument("--instance", choices=("operation", "development"))
    return parser


def _read_pipe_payload(handle_text: str) -> dict[str, Any]:
    try:
        handle = int(handle_text, 10)
    except ValueError as exc:
        raise ValueError("KIS_MCP_SECRET_INPUT_PIPE_INVALID") from exc

    if os.name == "nt":
        import msvcrt

        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY)
    else:  # pragma: no cover - production launch is Windows
        descriptor = handle
    with os.fdopen(descriptor, "rb", closefd=True) as pipe:
        raw = pipe.read(_MAX_PIPE_INPUT_BYTES + 1)
    if len(raw) > _MAX_PIPE_INPUT_BYTES:
        raise ValueError("KIS_MCP_SECRET_INPUT_PIPE_TOO_LARGE")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("KIS_MCP_SECRET_INPUT_INVALID") from exc
    if not isinstance(value, dict):
        raise ValueError("KIS_MCP_SECRET_INPUT_INVALID")
    return value


def _unlock_payload(environ: Mapping[str, str]) -> dict[str, Any]:
    if environ.get(BOOTSTRAP_ENVIRONMENT):
        return {}
    handle = environ.get(PIPE_HANDLE_ENVIRONMENT)
    if not handle:
        raise ValueError("KIS_MCP_SECRET_INPUT_PIPE_REQUIRED")
    return _read_pipe_payload(handle)


def _scrub_unlock_environment(environ: dict[str, str]) -> None:
    for name in (BOOTSTRAP_ENVIRONMENT, PIPE_HANDLE_ENVIRONMENT):
        environ.pop(name, None)
        os.environ.pop(name, None)


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    selected_environment = dict(os.environ if environ is None else environ)
    payload: dict[str, Any] = {}
    try:
        arguments = _parser().parse_args(list(argv) if argv is not None else None)
        payload = _unlock_payload(selected_environment)
        service = build_service(selected_environment)
        unlock_service(service, payload, selected_environment)
        _scrub_unlock_environment(selected_environment)
        set_active_secrets_service(service)

        if arguments.runtime == "remote":
            from kis_mcp.remote_runtime import main as remote_main

            remote_args = [] if arguments.instance is None else ["--instance", arguments.instance]
            remote_main(remote_args)
        else:
            from kis_mcp.server import main as server_main

            server_main()
        return 0
    except (SecretsError, ValueError, OSError, RuntimeError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    finally:
        payload.clear()
        clear_active_secrets_service()


if __name__ == "__main__":
    raise SystemExit(main())
