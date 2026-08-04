from __future__ import annotations

import json
from pathlib import Path

import pytest

import kis_mcp.providers.supabase.server as server_module
from kis_mcp.providers.supabase.config import load_supabase_provider_config
from kis_mcp.providers.supabase.runtime import SupabaseProviderRuntimeError


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONFIG = load_supabase_provider_config(REPOSITORY_ROOT)


def test_check_mode_is_non_network_and_redacted(monkeypatch, capsys) -> None:
    monkeypatch.setenv("SUPABASE_PROJECT_REF", "test-project")
    monkeypatch.setenv("SUPABASE_ACCESS_TOKEN", "test-token")
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
    assert payload["project_scoped"] is True
    assert "test-token" not in json.dumps(payload)
    assert "test-project" not in json.dumps(payload)


def test_check_mode_reports_not_ready_without_credentials(monkeypatch, capsys) -> None:
    monkeypatch.delenv("SUPABASE_PROJECT_REF", raising=False)
    monkeypatch.delenv("SUPABASE_ACCESS_TOKEN", raising=False)

    result = server_module.main(["--check"], config=CONFIG)
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["ready"] is False
    assert payload["project_ref_present"] is False
    assert payload["access_token_present"] is False


def test_normal_mode_runs_configured_stdio_server(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_PROJECT_REF", "test-project")
    monkeypatch.setenv("SUPABASE_ACCESS_TOKEN", "test-token")
    captured: dict[str, object] = {}

    class FakeServer:
        def run(self, *, transport: str) -> None:
            captured["transport"] = transport

    monkeypatch.setattr(
        server_module,
        "build_server",
        lambda config, environment: FakeServer(),
    )

    result = server_module.main([], config=CONFIG)

    assert result == 0
    assert captured == {"transport": "stdio"}


def test_normal_mode_rejects_missing_credentials(monkeypatch) -> None:
    monkeypatch.delenv("SUPABASE_PROJECT_REF", raising=False)
    monkeypatch.delenv("SUPABASE_ACCESS_TOKEN", raising=False)

    with pytest.raises(SupabaseProviderRuntimeError, match="SUPABASE_PROJECT_REF"):
        server_module.main([], config=CONFIG)
