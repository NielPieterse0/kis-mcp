from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import kis_mcp.providers.supabase.runtime as runtime_module
from kis_mcp.providers.supabase.config import load_supabase_provider_config
from kis_mcp.providers.supabase.runtime import (
    SupabaseProviderRuntimeError,
    build_oauth_token_storage,
    build_upstream_url,
    provider_readiness,
    require_project_scope,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONFIG = load_supabase_provider_config(REPOSITORY_ROOT)
ENVIRONMENT = {"SUPABASE_PROJECT_REF": "test-project"}


def test_default_url_is_project_scoped_read_write_without_pat() -> None:
    url = build_upstream_url(CONFIG, ENVIRONMENT)

    assert url == "https://mcp.supabase.com/mcp?project_ref=test-project"
    assert "read_only" not in url
    assert "features" not in url
    assert "token" not in url.lower()


def test_url_encodes_project_reference() -> None:
    url = build_upstream_url(
        CONFIG,
        {"SUPABASE_PROJECT_REF": "project ref/+"},
    )

    assert url.endswith("project_ref=project+ref%2F%2B")


def test_read_only_and_features_map_to_official_query_parameters() -> None:
    config = replace(CONFIG, read_only=True, features=("database", "docs"))

    url = build_upstream_url(config, ENVIRONMENT)

    assert url == (
        "https://mcp.supabase.com/mcp?"
        "project_ref=test-project&read_only=true&features=database%2Cdocs"
    )


def test_project_scope_is_trimmed() -> None:
    project_ref = require_project_scope(
        CONFIG,
        {"SUPABASE_PROJECT_REF": "  test-project  "},
    )

    assert project_ref == "test-project"


@pytest.mark.parametrize(
    "environment",
    [
        {},
        {"SUPABASE_PROJECT_REF": "   "},
    ],
)
def test_missing_project_scope_is_corrective(
    environment: dict[str, str],
) -> None:
    with pytest.raises(SupabaseProviderRuntimeError, match="SUPABASE_PROJECT_REF"):
        require_project_scope(CONFIG, environment)


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


def test_readiness_is_redacted_and_ready_for_oauth_preflight() -> None:
    readiness = provider_readiness(
        CONFIG,
        ENVIRONMENT,
        keyring_available=True,
    )
    rendered = json.dumps(readiness.as_dict(), sort_keys=True)

    assert readiness.ready is True
    assert readiness.project_scoped is True
    assert readiness.project_ref_present is True
    assert readiness.authentication_mode == "oauth-dcr"
    assert readiness.token_storage == "windows-keyring"
    assert readiness.token_storage_available is True
    assert readiness.legacy_pat_conflict is False
    assert readiness.endpoint_kind == "hosted"
    assert "test-project" not in rendered
    assert "SUPABASE_PROJECT_REF" not in rendered
    assert "SUPABASE_ACCESS_TOKEN" not in rendered


def test_readiness_rejects_legacy_pat_conflict_without_exposing_value() -> None:
    readiness = provider_readiness(
        CONFIG,
        {
            "SUPABASE_PROJECT_REF": "test-project",
            "SUPABASE_ACCESS_TOKEN": "forbidden-test-token",
        },
        keyring_available=True,
    )
    rendered = json.dumps(readiness.as_dict(), sort_keys=True)

    assert readiness.ready is False
    assert readiness.legacy_pat_conflict is True
    assert "forbidden-test-token" not in rendered
    assert "SUPABASE_ACCESS_TOKEN" not in rendered


def test_readiness_reports_missing_scope_or_keyring() -> None:
    missing_scope = provider_readiness(CONFIG, {}, keyring_available=True)
    missing_keyring = provider_readiness(CONFIG, ENVIRONMENT, keyring_available=False)

    assert missing_scope.ready is False
    assert missing_scope.project_ref_present is False
    assert missing_keyring.ready is False
    assert missing_keyring.token_storage_available is False
