from __future__ import annotations

import json
from pathlib import Path

import kis_mcp.providers.supabase.runtime as runtime_module
import kis_mcp.providers.supabase.server as server_module
from kis_mcp.providers.supabase.config import load_supabase_provider_config


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONFIG = load_supabase_provider_config(REPOSITORY_ROOT)


def test_check_mode_is_non_network_redacted_account_oauth_preflight(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("SUPABASE_PROJECT_REF", raising=False)
    monkeypatch.delenv("SUPABASE_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(runtime_module, "windows_keyring_available", lambda: True)
    monkeypatch.setattr(
        server_module,
        "build_transport",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("check mode must not construct an upstream transport")
        ),
    )

    result = server_module.main(["--check"], config=CONFIG)
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["ready"] is True
    assert payload["account_scoped"] is True
    assert payload["project_routing"] == "registered_per_call"
    assert payload["authentication_mode"] == "oauth-dcr"
    assert payload["token_storage"] == "windows-keyring"
    assert payload["legacy_pat_conflict"] is False
    rendered = json.dumps(payload)
    assert "SUPABASE_PROJECT_REF" not in rendered
    assert "SUPABASE_ACCESS_TOKEN" not in rendered


def test_check_mode_does_not_depend_on_legacy_project_scope(monkeypatch, capsys) -> None:
    monkeypatch.setenv("SUPABASE_PROJECT_REF", "legacy-project")
    monkeypatch.delenv("SUPABASE_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(runtime_module, "windows_keyring_available", lambda: True)

    result = server_module.main(["--check"], config=CONFIG)
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["ready"] is True
    assert payload["account_scoped"] is True
    assert "legacy-project" not in json.dumps(payload)


def test_check_mode_reports_legacy_pat_conflict(monkeypatch, capsys) -> None:
    monkeypatch.delenv("SUPABASE_PROJECT_REF", raising=False)
    monkeypatch.setenv("SUPABASE_ACCESS_TOKEN", "forbidden-test-token")
    monkeypatch.setattr(runtime_module, "windows_keyring_available", lambda: True)

    result = server_module.main(["--check"], config=CONFIG)
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["ready"] is False
    assert payload["legacy_pat_conflict"] is True
    assert "forbidden-test-token" not in json.dumps(payload)


def test_normal_mode_runs_configured_stdio_server_without_project_environment(
    monkeypatch,
) -> None:
    monkeypatch.delenv("SUPABASE_PROJECT_REF", raising=False)
    monkeypatch.delenv("SUPABASE_ACCESS_TOKEN", raising=False)
    captured: dict[str, object] = {}

    class FakeServer:
        def run(self, *, transport: str) -> None:
            captured["transport"] = transport

    def fake_build_server(config, environment):
        captured["legacy_project_env_present"] = "SUPABASE_PROJECT_REF" in environment
        return FakeServer()

    monkeypatch.setattr(server_module, "build_server", fake_build_server)

    result = server_module.main([], config=CONFIG)

    assert result == 0
    assert captured == {
        "legacy_project_env_present": False,
        "transport": "stdio",
    }
