from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import kis_mcp.providers.supabase.runtime as runtime_module
from kis_mcp.providers.supabase.config import load_supabase_provider_config
from kis_mcp.providers.supabase.runtime import (
    build_oauth_token_storage,
    build_upstream_url,
    provider_readiness,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONFIG = load_supabase_provider_config(REPOSITORY_ROOT)


def test_default_url_is_unscoped_read_write_without_pat() -> None:
    url = build_upstream_url(CONFIG)

    assert url == "https://mcp.supabase.com/mcp"
    assert "project_ref" not in url
    assert "project_id" not in url
    assert "token" not in url.lower()


def test_read_only_and_features_map_to_official_query_parameters() -> None:
    config = replace(CONFIG, read_only=True, features=("database", "docs"))

    url = build_upstream_url(config)

    assert url == (
        "https://mcp.supabase.com/mcp?read_only=true&features=database%2Cdocs"
    )


def test_build_oauth_token_storage_uses_configured_windows_keyring(monkeypatch) -> None:
    captured: dict[str, object] = {}
    sentinel = object()

    def fake_keyring_store(**kwargs: object) -> object:
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(runtime_module, "KeyringStore", fake_keyring_store)

    result = build_oauth_token_storage(CONFIG)

    assert result is sentinel
    assert captured["service_name"] == "kis-mcp/supabase"
    assert captured["key_sanitization_strategy"] is not None
    assert captured["collection_sanitization_strategy"] is not None


def test_readiness_is_account_scoped_and_ready_without_project_environment() -> None:
    readiness = provider_readiness(CONFIG, {}, keyring_available=True)
    rendered = json.dumps(readiness.as_dict(), sort_keys=True)

    assert readiness.ready is True
    assert readiness.account_scoped is True
    assert readiness.project_routing == "registered_per_call"
    assert readiness.authentication_mode == "oauth-dcr"
    assert readiness.token_storage == "windows-keyring"
    assert readiness.token_storage_available is True
    assert readiness.legacy_pat_conflict is False
    assert readiness.endpoint_kind == "hosted"
    assert "SUPABASE_PROJECT_REF" not in rendered
    assert "SUPABASE_ACCESS_TOKEN" not in rendered


def test_readiness_rejects_legacy_pat_conflict_without_exposing_value() -> None:
    readiness = provider_readiness(
        CONFIG,
        {"SUPABASE_ACCESS_TOKEN": "forbidden-test-token"},
        keyring_available=True,
    )
    rendered = json.dumps(readiness.as_dict(), sort_keys=True)

    assert readiness.ready is False
    assert readiness.legacy_pat_conflict is True
    assert "forbidden-test-token" not in rendered
    assert "SUPABASE_ACCESS_TOKEN" not in rendered


def test_readiness_reports_missing_keyring() -> None:
    missing_keyring = provider_readiness(CONFIG, {}, keyring_available=False)

    assert missing_keyring.ready is False
    assert missing_keyring.token_storage_available is False
