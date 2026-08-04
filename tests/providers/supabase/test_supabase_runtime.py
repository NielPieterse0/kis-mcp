from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from kis_mcp.providers.supabase.config import load_supabase_provider_config
from kis_mcp.providers.supabase.runtime import (
    SupabaseProviderRuntimeError,
    build_upstream_url,
    provider_readiness,
    require_runtime_credentials,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONFIG = load_supabase_provider_config(REPOSITORY_ROOT)
ENVIRONMENT = {
    "SUPABASE_PROJECT_REF": "test-project",
    "SUPABASE_ACCESS_TOKEN": "test-token",
}


def test_default_url_is_project_scoped_read_write() -> None:
    url = build_upstream_url(CONFIG, ENVIRONMENT)

    assert url == "https://mcp.supabase.com/mcp?project_ref=test-project"
    assert "read_only" not in url
    assert "features" not in url
    assert "test-token" not in url


def test_url_encodes_project_reference() -> None:
    environment = dict(ENVIRONMENT)
    environment["SUPABASE_PROJECT_REF"] = "project ref/+"

    url = build_upstream_url(CONFIG, environment)

    assert url.endswith("project_ref=project+ref%2F%2B")


def test_read_only_and_features_map_to_official_query_parameters() -> None:
    config = replace(CONFIG, read_only=True, features=("database", "docs"))

    url = build_upstream_url(config, ENVIRONMENT)

    assert url == (
        "https://mcp.supabase.com/mcp?"
        "project_ref=test-project&read_only=true&features=database%2Cdocs"
    )


def test_runtime_credentials_are_trimmed() -> None:
    project_ref, access_token = require_runtime_credentials(
        CONFIG,
        {
            "SUPABASE_PROJECT_REF": "  test-project  ",
            "SUPABASE_ACCESS_TOKEN": "  test-token  ",
        },
    )

    assert project_ref == "test-project"
    assert access_token == "test-token"


@pytest.mark.parametrize(
    ("environment", "message"),
    [
        ({"SUPABASE_ACCESS_TOKEN": "test-token"}, "SUPABASE_PROJECT_REF"),
        ({"SUPABASE_PROJECT_REF": "test-project"}, "SUPABASE_ACCESS_TOKEN"),
        (
            {
                "SUPABASE_PROJECT_REF": "   ",
                "SUPABASE_ACCESS_TOKEN": "test-token",
            },
            "SUPABASE_PROJECT_REF",
        ),
    ],
)
def test_missing_runtime_credentials_are_corrective(
    environment: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(SupabaseProviderRuntimeError, match=message):
        require_runtime_credentials(CONFIG, environment)


def test_readiness_is_redacted_and_ready_when_credentials_exist() -> None:
    readiness = provider_readiness(CONFIG, ENVIRONMENT)
    rendered = json.dumps(readiness.as_dict(), sort_keys=True)

    assert readiness.ready is True
    assert readiness.project_scoped is True
    assert readiness.project_ref_present is True
    assert readiness.access_token_present is True
    assert readiness.endpoint_kind == "hosted"
    assert readiness.read_only is False
    assert readiness.features == ()
    assert "test-token" not in rendered
    assert "test-project" not in rendered
    assert "SUPABASE_ACCESS_TOKEN" not in rendered
    assert "SUPABASE_PROJECT_REF" not in rendered


def test_readiness_reports_missing_credentials_without_values() -> None:
    readiness = provider_readiness(CONFIG, {})

    assert readiness.ready is False
    assert readiness.project_ref_present is False
    assert readiness.access_token_present is False
    assert readiness.as_dict()["ready"] is False


def test_readiness_identifies_official_hosted_endpoint() -> None:
    readiness = provider_readiness(CONFIG, ENVIRONMENT)

    assert readiness.endpoint_kind == "hosted"
