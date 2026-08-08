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


def test_loads_checked_in_oauth_provider_configuration() -> None:
    config = load_supabase_provider_config(REPOSITORY_ROOT)

    assert config.schema_version == 3
    assert config.provider_id == "supabase"
    assert config.server_name == "kis-mcp-supabase"
    assert config.source_repository == "https://github.com/supabase/mcp"
    assert config.source_revision == "5cda0672702c65fe672280ee4cf306593e643fb6"
    assert config.base_url == "https://mcp.supabase.com/mcp"
    assert not hasattr(config, "project_ref_env")
    assert config.auth_mode == "oauth-dcr"
    assert config.client_name == "kis-mcp Supabase"
    assert config.token_storage == "windows-keyring"
    assert config.keyring_service == "kis-mcp/supabase"
    assert config.legacy_pat_env == "SUPABASE_ACCESS_TOKEN"
    assert config.callback_host == "localhost"
    assert config.callback_timeout_seconds == 300
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


def test_rejects_legacy_pat_transport_configuration(tmp_path: Path) -> None:
    value = _checked_in_config()
    upstream = deepcopy(value["upstream"])
    assert isinstance(upstream, dict)
    upstream["access_token_env"] = "SUPABASE_ACCESS_TOKEN"
    value["upstream"] = upstream
    _write_config(tmp_path, value)

    with pytest.raises(
        SupabaseProviderConfigError,
        match="upstream has unknown keys: access_token_env",
    ):
        load_supabase_provider_config(tmp_path)


def test_rejects_embedded_oauth_secret_key(tmp_path: Path) -> None:
    value = _checked_in_config()
    authentication = deepcopy(value["authentication"])
    assert isinstance(authentication, dict)
    authentication["client_secret"] = "forbidden-test-value"
    value["authentication"] = authentication
    _write_config(tmp_path, value)

    with pytest.raises(
        SupabaseProviderConfigError,
        match="authentication has unknown keys: client_secret",
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


def test_rejects_disabled_tls_verification(tmp_path: Path) -> None:
    value = _checked_in_config()
    upstream = deepcopy(value["upstream"])
    assert isinstance(upstream, dict)
    upstream["verify_tls"] = False
    value["upstream"] = upstream
    _write_config(tmp_path, value)

    with pytest.raises(SupabaseProviderConfigError, match="verify_tls must remain true"):
        load_supabase_provider_config(tmp_path)


def test_rejects_non_oauth_authentication_mode(tmp_path: Path) -> None:
    value = _checked_in_config()
    authentication = deepcopy(value["authentication"])
    assert isinstance(authentication, dict)
    authentication["mode"] = "pat"
    value["authentication"] = authentication
    _write_config(tmp_path, value)

    with pytest.raises(SupabaseProviderConfigError, match="mode must be oauth-dcr"):
        load_supabase_provider_config(tmp_path)


def test_rejects_non_keyring_token_storage(tmp_path: Path) -> None:
    value = _checked_in_config()
    authentication = deepcopy(value["authentication"])
    assert isinstance(authentication, dict)
    authentication["token_storage"] = "file"
    value["authentication"] = authentication
    _write_config(tmp_path, value)

    with pytest.raises(SupabaseProviderConfigError, match="token_storage must be windows-keyring"):
        load_supabase_provider_config(tmp_path)


def test_rejects_invalid_environment_variable_name(tmp_path: Path) -> None:
    value = _checked_in_config()
    authentication = deepcopy(value["authentication"])
    assert isinstance(authentication, dict)
    authentication["legacy_pat_env"] = "not an env name"
    value["authentication"] = authentication
    _write_config(tmp_path, value)

    with pytest.raises(SupabaseProviderConfigError, match="legacy_pat_env"):
        load_supabase_provider_config(tmp_path)


def test_rejects_non_loopback_callback_host(tmp_path: Path) -> None:
    value = _checked_in_config()
    authentication = deepcopy(value["authentication"])
    assert isinstance(authentication, dict)
    authentication["callback_host"] = "0.0.0.0"
    value["authentication"] = authentication
    _write_config(tmp_path, value)

    with pytest.raises(SupabaseProviderConfigError, match="callback_host must be localhost"):
        load_supabase_provider_config(tmp_path)


def test_rejects_non_positive_callback_timeout(tmp_path: Path) -> None:
    value = _checked_in_config()
    authentication = deepcopy(value["authentication"])
    assert isinstance(authentication, dict)
    authentication["callback_timeout_seconds"] = 0
    value["authentication"] = authentication
    _write_config(tmp_path, value)

    with pytest.raises(SupabaseProviderConfigError, match="callback_timeout_seconds"):
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
