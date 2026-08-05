from __future__ import annotations

import base64
import os

from kis_mcp.secrets.cli import BOOTSTRAP_ENVIRONMENT
from kis_mcp.secrets.launcher import (
    PIPE_HANDLE_ENVIRONMENT,
    _scrub_unlock_environment,
    _unlock_payload,
)


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
