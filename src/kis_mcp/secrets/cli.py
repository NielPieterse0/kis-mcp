from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TextIO

from .crypto import decode_bootstrap_key
from .errors import SecretsError
from .service import SecretsService
from .vault import VaultStore


DEFAULT_SECRETS_ROOT = Path(r"C:\Projects\.kis-mcp\secrets")
PROJECT_BOUNDARY = Path(r"C:\Projects")
ROOT_ENVIRONMENT = "KIS_MCP_SECRETS_ROOT"
BOOTSTRAP_ENVIRONMENT = "KIS_MCP_VAULT_KEY"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kis-mcp-secrets")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("initialize")
    subparsers.add_parser("status")
    subparsers.add_parser("list")
    set_parser = subparsers.add_parser("set")
    set_parser.add_argument("--reference", required=True)
    resolve_parser = subparsers.add_parser("resolve-internal")
    resolve_parser.add_argument("--reference", required=True)
    subparsers.add_parser("rotate")
    subparsers.add_parser("verify-unlock")
    return parser


def resolve_secrets_root(environ: Mapping[str, str]) -> Path:
    raw = environ.get(ROOT_ENVIRONMENT, str(DEFAULT_SECRETS_ROOT))
    root = Path(raw)
    if not root.is_absolute():
        raise ValueError("KIS_MCP_SECRET_ROOT_INVALID")
    resolved = root.resolve()
    if os.name == "nt":
        boundary = PROJECT_BOUNDARY.resolve()
        try:
            resolved.relative_to(boundary)
        except ValueError as exc:
            raise ValueError("KIS_MCP_SECRET_ROOT_OUTSIDE_PROJECT_BOUNDARY") from exc
    return resolved


def build_service(environ: Mapping[str, str]) -> SecretsService:
    return SecretsService(VaultStore(resolve_secrets_root(environ)))


def _read_payload(stdin: TextIO) -> dict[str, Any]:
    raw = stdin.read()
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("KIS_MCP_SECRET_INPUT_INVALID") from exc
    if not isinstance(value, dict):
        raise ValueError("KIS_MCP_SECRET_INPUT_INVALID")
    return value


def _required_text(payload: Mapping[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"KIS_MCP_SECRET_INPUT_MISSING: {name}")
    return value


def _bootstrap_key(environ: Mapping[str, str]) -> bytes | None:
    encoded = environ.get(BOOTSTRAP_ENVIRONMENT)
    if encoded is None:
        return None
    return decode_bootstrap_key(encoded)


def _initialize(
    service: SecretsService,
    payload: Mapping[str, Any],
    environ: Mapping[str, str],
) -> None:
    key = _bootstrap_key(environ)
    if key is not None:
        service.initialize_with_key(key)
        return
    service.initialize(_required_text(payload, "unlock"))


def unlock_service(
    service: SecretsService,
    payload: Mapping[str, Any],
    environ: Mapping[str, str],
) -> None:
    key = _bootstrap_key(environ)
    if key is not None:
        service.unlock_with_key(key)
        return
    service.unlock(_required_text(payload, "unlock"))


def _write_json(stdout: TextIO, value: Mapping[str, Any]) -> None:
    stdout.write(json.dumps(value, sort_keys=True, separators=(",", ":")))
    stdout.write("\n")


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    selected_stdin = stdin or sys.stdin
    selected_stdout = stdout or sys.stdout
    selected_stderr = stderr or sys.stderr
    selected_environment = dict(os.environ if environ is None else environ)
    try:
        arguments = _parser().parse_args(list(argv) if argv is not None else None)
        payload = _read_payload(selected_stdin)
        service = build_service(selected_environment)

        if arguments.command == "initialize":
            _initialize(service, payload, selected_environment)
            _write_json(selected_stdout, service.status().to_dict())
        elif arguments.command == "status":
            _write_json(selected_stdout, service.status().to_dict())
        elif arguments.command == "list":
            _write_json(
                selected_stdout,
                {
                    "schema_version": 1,
                    "references": [
                        record.to_dict() for record in service.list_references()
                    ],
                },
            )
        elif arguments.command == "set":
            unlock_service(service, payload, selected_environment)
            service.set_secret(arguments.reference, _required_text(payload, "value"))
            _write_json(selected_stdout, service.status().to_dict())
        elif arguments.command == "resolve-internal":
            unlock_service(service, payload, selected_environment)
            selected_stdout.write(service.resolve(arguments.reference))
        elif arguments.command == "rotate":
            unlock_service(service, payload, selected_environment)
            service.rotate_master_key(_required_text(payload, "new_unlock"))
            _write_json(selected_stdout, service.status().to_dict())
        elif arguments.command == "verify-unlock":
            unlock_service(service, payload, selected_environment)
            _write_json(selected_stdout, service.status().to_dict())
        else:  # pragma: no cover - argparse owns the closed command set
            raise ValueError("KIS_MCP_SECRET_COMMAND_INVALID")
        return 0
    except (SecretsError, ValueError, OSError, RuntimeError) as exc:
        selected_stderr.write(f"{exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
