from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from kis_mcp.config import load_runtime_config
from kis_mcp.remote_runtime import run_remote_instance


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _configuration_copy(tmp_path: Path) -> Path:
    root = tmp_path / "configuration-copy"
    (root / "settings").mkdir(parents=True)
    (root / "policy").mkdir()
    for relative in ("settings/kis-mcp.settings.json", "policy/kis-mcp.policy.json"):
        target = root / relative
        target.write_text((REPOSITORY_ROOT / relative).read_text(encoding="utf-8"), encoding="utf-8")
    return root


def test_remote_instances_are_distinct_and_settings_driven() -> None:
    config = load_runtime_config(REPOSITORY_ROOT)

    operation = config.remote_instance("operation")
    development = config.remote_instance("development")

    assert config.active_remote_instance == "operation"
    assert operation.host == development.host == "127.0.0.1"
    assert operation.path == development.path == "/mcp"
    assert operation.port != development.port
    assert operation.profile_name != development.profile_name
    assert operation.tunnel_id == "tunnel_6a6806687cf88191bf97c8c3cb0d1f61"
    assert development.tunnel_id == "tunnel_6a68065a7b688191ba706b86151241ff"
    assert operation.configured is development.configured is True
    assert operation.tunnel_credential_target == "kis-mcp/tunnel/operation"
    assert development.tunnel_credential_target == "kis-mcp/tunnel/development"
    assert config.tunnel_client_path == r"C:\Tools\openai-tunnel-client\tunnel-client.exe"


def test_remote_transport_rejects_non_loopback_host(tmp_path: Path) -> None:
    root = _configuration_copy(tmp_path)
    settings_path = root / "settings" / "kis-mcp.settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings["remote_mcp"]["host"] = "0.0.0.0"
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="loopback"):
        load_runtime_config(root)


def test_unknown_remote_instance_is_rejected() -> None:
    config = load_runtime_config(REPOSITORY_ROOT)

    with pytest.raises(RuntimeError, match="Unknown remote MCP instance"):
        config.remote_instance("staging")


def test_remote_runtime_uses_streamable_http_arguments() -> None:
    config = load_runtime_config(REPOSITORY_ROOT)
    calls: list[dict[str, Any]] = []

    class FakeServer:
        def run(self, **kwargs: Any) -> None:
            calls.append(kwargs)

    run_remote_instance(config, "development", server_factory=lambda _: FakeServer())

    instance = config.remote_instance("development")
    assert calls == [
        {
            "transport": "http",
            "host": instance.host,
            "port": instance.port,
            "path": instance.path,
            "stateless_http": False,
            "json_response": True,
            "show_banner": False,
        }
    ]
