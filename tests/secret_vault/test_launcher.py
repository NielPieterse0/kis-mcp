from __future__ import annotations

import base64
import os
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from kis_mcp.secrets.cli import BOOTSTRAP_ENVIRONMENT, ROOT_ENVIRONMENT
from kis_mcp.secrets.launcher import (
    PIPE_HANDLE_ENVIRONMENT,
    _scrub_unlock_environment,
    _unlock_payload,
    main,
)
from kis_mcp.secrets.runtime import get_active_secrets_service
from kis_mcp.secrets.service import SecretsService
from kis_mcp.secrets.vault import VaultStore


def test_bootstrap_mode_does_not_require_interactive_pipe() -> None:
    encoded = base64.b64encode(b"b" * 32).decode("ascii")

    assert _unlock_payload({BOOTSTRAP_ENVIRONMENT: encoded}) == {}


def test_unlock_environment_is_scrubbed_after_service_unlock(monkeypatch) -> None:
    encoded = base64.b64encode(b"b" * 32).decode("ascii")
    selected = {
        BOOTSTRAP_ENVIRONMENT: encoded,
        PIPE_HANDLE_ENVIRONMENT: "1234",
        "UNRELATED": "preserved",
    }
    monkeypatch.setenv(BOOTSTRAP_ENVIRONMENT, encoded)
    monkeypatch.setenv(PIPE_HANDLE_ENVIRONMENT, "1234")

    _scrub_unlock_environment(selected)

    assert BOOTSTRAP_ENVIRONMENT not in selected
    assert PIPE_HANDLE_ENVIRONMENT not in selected
    assert selected["UNRELATED"] == "preserved"
    assert BOOTSTRAP_ENVIRONMENT not in os.environ
    assert PIPE_HANDLE_ENVIRONMENT not in os.environ


def _runtime_root() -> Path:
    return Path.cwd() / ".work" / "runtime-tests" / f"launcher-{uuid4().hex}"


def test_launcher_scrubs_bootstrap_environment_when_unlock_fails(monkeypatch) -> None:
    root = _runtime_root()
    encoded = base64.b64encode(b"b" * 32).decode("ascii")
    monkeypatch.setenv(BOOTSTRAP_ENVIRONMENT, encoded)
    try:
        code = main(
            [],
            environ={
                ROOT_ENVIRONMENT: str(root),
                BOOTSTRAP_ENVIRONMENT: encoded,
            },
        )

        assert code == 2
        assert BOOTSTRAP_ENVIRONMENT not in os.environ
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_launcher_scrubs_pipe_handle_when_payload_is_invalid(monkeypatch) -> None:
    root = _runtime_root()
    monkeypatch.setenv(PIPE_HANDLE_ENVIRONMENT, "not-a-handle")
    try:
        code = main(
            [],
            environ={
                ROOT_ENVIRONMENT: str(root),
                PIPE_HANDLE_ENVIRONMENT: "not-a-handle",
            },
        )

        assert code == 2
        assert PIPE_HANDLE_ENVIRONMENT not in os.environ
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_launcher_exposes_unlocked_service_only_during_runtime(
    monkeypatch,
) -> None:
    root = _runtime_root()
    key = b"b" * 32
    encoded = base64.b64encode(key).decode("ascii")
    SecretsService(VaultStore(root)).initialize_with_key(key)
    observed: dict[str, bool] = {}

    import kis_mcp.server as server_module

    def fake_server_main() -> None:
        observed["unlocked"] = get_active_secrets_service().status().unlocked

    monkeypatch.setattr(server_module, "main", fake_server_main)
    monkeypatch.setenv(BOOTSTRAP_ENVIRONMENT, encoded)
    try:
        code = main(
            [],
            environ={
                ROOT_ENVIRONMENT: str(root),
                BOOTSTRAP_ENVIRONMENT: encoded,
            },
        )

        assert code == 0
        assert observed == {"unlocked": True}
        assert BOOTSTRAP_ENVIRONMENT not in os.environ
        with pytest.raises(
            RuntimeError,
            match="KIS_MCP_SECRET_SERVICE_NOT_INITIALIZED",
        ):
            get_active_secrets_service()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_launcher_clears_unlocked_service_when_runtime_fails(monkeypatch) -> None:
    root = _runtime_root()
    key = b"c" * 32
    encoded = base64.b64encode(key).decode("ascii")
    SecretsService(VaultStore(root)).initialize_with_key(key)

    import kis_mcp.server as server_module

    def failing_server_main() -> None:
        assert get_active_secrets_service().status().unlocked is True
        raise RuntimeError("STARTUP_RUNTIME_FAILURE")

    monkeypatch.setattr(server_module, "main", failing_server_main)
    monkeypatch.setenv(BOOTSTRAP_ENVIRONMENT, encoded)
    try:
        code = main(
            [],
            environ={
                ROOT_ENVIRONMENT: str(root),
                BOOTSTRAP_ENVIRONMENT: encoded,
            },
        )

        assert code == 2
        assert BOOTSTRAP_ENVIRONMENT not in os.environ
        with pytest.raises(
            RuntimeError,
            match="KIS_MCP_SECRET_SERVICE_NOT_INITIALIZED",
        ):
            get_active_secrets_service()
    finally:
        shutil.rmtree(root, ignore_errors=True)
