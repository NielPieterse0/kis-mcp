from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from kis_mcp.providers.supabase.config import (
    SupabaseProviderConfigError,
    load_supabase_provider_config,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPOSITORY_ROOT / "settings" / "providers" / "supabase-mcp.provider.json"


def _checked_in_config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _write_config(tmp_path: Path, value: dict[str, object]) -> Path:
    path = tmp_path / "settings" / "providers" / "supabase-mcp.provider.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_loads_checked_in_provider_configuration() -> None:
    config = load_supabase_provider_config(REPOSITORY_ROOT)

    assert config.provider_id == "supabase"
    assert config.server_name == "kis-mcp-supabase"
    assert config.source_repository == "https://github.com/supabase/mcp"
    assert config.source_revision == "5cda0672702c65fe672280ee4cf306593e643fb6"
    assert config.base_url == "https://mcp.supabase.com/mcp"
    assert config.project_ref_env == "SUPABASE_PROJECT_REF"
    assert config.access_token_env == "SUPABASE_ACCESS_TOKEN"
    assert config.read_only is False
    assert config.features == ()
    assert config.verify_tls is True
    assert config.downstream_transport == "stdio"


def test_rejects_unknown_root_key(tmp_path: Path) -> None:
    value = _checked_in_config()
    value["secret"] = "forbidden"
    _write_config(tmp_path, value)

    with pytest.raises(SupabaseProviderConfigError, match="root has unknown keys: secret"):
        load_supabase_provider_config(tmp_path)


def test_rejects_embedded_access_token_key(tmp_path: Path) -> None:
    value = _checked_in_config()
    upstream = deepcopy(value["upstream"])
    assert isinstance(upstream, dict)
    upstream["access_token"] = "forbidden-test-value"
    value["upstream"] = upstream
    _write_config(tmp_path, value)

    with pytest.raises(
        SupabaseProviderConfigError,
        match="upstream has unknown keys: access_token",
    ):
        load_supabase_provider_config(tmp_path)


def test_rejects_arbitrary_external_endpoint(tmp_path: Path) -> None:
    value = _checked_in_config()
    upstream = deepcopy(value["upstream"])
    assert isinstance(upstream, dict)
    upstream["base_url"] = "https://example.com/mcp"
    value["upstream"] = upstream
    _write_config(tmp_path, value)

    with pytest.raises(SupabaseProviderConfigError, match="official hosted endpoint"):
        load_supabase_provider_config(tmp_path)


def test_rejects_loopback_endpoint_that_could_receive_the_pat(tmp_path: Path) -> None:
    value = _checked_in_config()
    upstream = deepcopy(value["upstream"])
    assert isinstance(upstream, dict)
    upstream["base_url"] = "http://localhost:54321/mcp"
    value["upstream"] = upstream
    _write_config(tmp_path, value)

    with pytest.raises(SupabaseProviderConfigError, match="official hosted endpoint"):
        load_supabase_provider_config(tmp_path)


def test_rejects_disabled_tls_verification(tmp_path: Path) -> None:
    value = _checked_in_config()
    upstream = deepcopy(value["upstream"])
    assert isinstance(upstream, dict)
    upstream["verify_tls"] = False
    value["upstream"] = upstream
    _write_config(tmp_path, value)

    with pytest.raises(SupabaseProviderConfigError, match="verify_tls must remain true"):
        load_supabase_provider_config(tmp_path)


def test_rejects_invalid_environment_variable_name(tmp_path: Path) -> None:
    value = _checked_in_config()
    upstream = deepcopy(value["upstream"])
    assert isinstance(upstream, dict)
    upstream["access_token_env"] = "not an env name"
    value["upstream"] = upstream
    _write_config(tmp_path, value)

    with pytest.raises(SupabaseProviderConfigError, match="access_token_env"):
        load_supabase_provider_config(tmp_path)


def test_rejects_duplicate_features(tmp_path: Path) -> None:
    value = _checked_in_config()
    upstream = deepcopy(value["upstream"])
    assert isinstance(upstream, dict)
    upstream["features"] = ["database", "database"]
    value["upstream"] = upstream
    _write_config(tmp_path, value)

    with pytest.raises(SupabaseProviderConfigError, match="features must not contain duplicates"):
        load_supabase_provider_config(tmp_path)


def test_rejects_non_boolean_read_only(tmp_path: Path) -> None:
    value = _checked_in_config()
    upstream = deepcopy(value["upstream"])
    assert isinstance(upstream, dict)
    upstream["read_only"] = "false"
    value["upstream"] = upstream
    _write_config(tmp_path, value)

    with pytest.raises(SupabaseProviderConfigError, match="read_only must be a boolean"):
        load_supabase_provider_config(tmp_path)


def test_rejects_unknown_nested_key(tmp_path: Path) -> None:
    value = _checked_in_config()
    provider = deepcopy(value["provider"])
    assert isinstance(provider, dict)
    provider["mode"] = "custom"
    value["provider"] = provider
    _write_config(tmp_path, value)

    with pytest.raises(SupabaseProviderConfigError, match="provider has unknown keys: mode"):
        load_supabase_provider_config(tmp_path)
