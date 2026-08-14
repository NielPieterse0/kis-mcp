from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "workspace-agent-trigger-probe.py"


def _load_probe():
    spec = importlib.util.spec_from_file_location("workspace_agent_trigger_probe", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_workflow_dispatch_normalizes_to_trigger_envelope():
    probe = _load_probe()
    event = {
        "inputs": {
            "mode": "validate",
            "conversation_key": "kis-mcp:issue:233",
            "input": "Validate workspace-agent triggering.",
            "idempotency_key": "evt-233",
        }
    }

    envelope = probe.normalize_event("workflow_dispatch", event, run_id="12345")

    assert envelope == {
        "mode": "validate",
        "conversation_key": "kis-mcp:issue:233",
        "input": "Validate workspace-agent triggering.",
        "idempotency_key": "evt-233",
    }


def test_repository_dispatch_uses_event_id_as_default_idempotency_key():
    probe = _load_probe()
    event = {
        "client_payload": {
            "mode": "live",
            "event_id": "wm_evt_abc",
            "conversation_key": "kis-mcp:issue:233",
            "input": "Run the feasibility trigger.",
        }
    }

    envelope = probe.normalize_event("repository_dispatch", event, run_id="999")

    assert envelope["mode"] == "live"
    assert envelope["idempotency_key"] == "github:repository_dispatch:wm_evt_abc"
    assert envelope["conversation_key"] == "kis-mcp:issue:233"


def test_build_request_matches_openai_workspace_agent_contract():
    probe = _load_probe()
    envelope = {
        "mode": "live",
        "conversation_key": "kis-mcp:issue:233",
        "input": "Trigger test",
        "idempotency_key": "evt-233",
    }

    request = probe.build_request(
        trigger_id="agtch_test_123",
        access_token="secret-token-value",
        envelope=envelope,
    )

    assert request.full_url == (
        "https://api.chatgpt.com/v1/workspace_agents/agtch_test_123/trigger"
    )
    assert request.get_method() == "POST"
    assert request.headers["Authorization"] == "Bearer secret-token-value"
    assert request.headers["Content-type"] == "application/json"
    assert request.headers["Idempotency-key"] == "evt-233"
    assert json.loads(request.data) == {
        "conversation_key": "kis-mcp:issue:233",
        "input": "Trigger test",
    }


class _FakeResponse:
    def __init__(self, status: int, body: bytes = b"") -> None:
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._body


def test_send_request_accepts_202_with_empty_body():
    probe = _load_probe()
    request = probe.build_request(
        trigger_id="agtch_test_123",
        access_token="secret-token-value",
        envelope={
            "conversation_key": "k",
            "input": "i",
            "idempotency_key": "e",
        },
    )
    opener = lambda request, timeout: _FakeResponse(202)

    result = probe.send_request(request, opener=opener)

    assert result == {"accepted": True, "status": 202}


def test_send_request_retains_documented_response_metadata():
    probe = _load_probe()
    request = probe.build_request(
        trigger_id="agtch_test_123",
        access_token="secret-token-value",
        envelope={
            "conversation_key": "k",
            "input": "i",
            "idempotency_key": "e",
        },
    )
    body = json.dumps(
        {
            "conversation_url": "https://chatgpt.com/c/123",
            "agent_trigger_run_id": "apirun_123",
        }
    ).encode("utf-8")
    opener = lambda request, timeout: _FakeResponse(202, body)

    result = probe.send_request(request, opener=opener)

    assert result == {
        "accepted": True,
        "status": 202,
        "conversation_url": "https://chatgpt.com/c/123",
        "agent_trigger_run_id": "apirun_123",
    }


def test_send_request_non_202_does_not_expose_token():
    probe = _load_probe()
    request = probe.build_request(
        trigger_id="agtch_test_123",
        access_token="secret-token-value",
        envelope={
            "conversation_key": "k",
            "input": "i",
            "idempotency_key": "e",
        },
    )
    opener = lambda request, timeout: _FakeResponse(409, b'{"error":"not runnable"}')

    with pytest.raises(RuntimeError) as error:
        probe.send_request(request, opener=opener)

    message = str(error.value)
    assert "409" in message
    assert "secret-token-value" not in message


def test_rejects_unsupported_event():
    probe = _load_probe()

    with pytest.raises(ValueError, match="UNSUPPORTED_GITHUB_EVENT"):
        probe.normalize_event("issues", {}, run_id="1")


def test_validate_mode_main_does_not_require_live_credentials(
    tmp_path, monkeypatch, capsys
):
    probe = _load_probe()
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "inputs": {
                    "mode": "validate",
                    "conversation_key": "kis-mcp:issue:233",
                    "input": "Validate only",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_WORKSPACE_AGENT_TRIGGER_ID", raising=False)
    monkeypatch.delenv("OPENAI_WORKSPACE_AGENT_ACCESS_TOKEN", raising=False)

    result = probe.main(
        [
            "--event-name",
            "workflow_dispatch",
            "--event-path",
            str(event_path),
            "--run-id",
            "123",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert '"validated": true' in captured.out
    assert "OPENAI_WORKSPACE_AGENT_ACCESS_TOKEN" not in captured.out


def test_workflow_supports_both_dispatch_paths_and_secret_storage():
    workflow = (
        Path(__file__).parents[2]
        / ".github"
        / "workflows"
        / "workspace-agent-trigger-probe.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "repository_dispatch:" in workflow
    assert "workspace-agent-trigger-probe" in workflow
    assert "${{ secrets.OPENAI_WORKSPACE_AGENT_ACCESS_TOKEN }}" in workflow
    assert "${{ vars.OPENAI_WORKSPACE_AGENT_TRIGGER_ID }}" in workflow
    assert "secret-token-value" not in workflow
