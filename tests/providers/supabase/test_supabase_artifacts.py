from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
AUTH_SCRIPT = REPOSITORY_ROOT / "scripts" / "auth-supabase-mcp.ps1"
SMOKE_SCRIPT = REPOSITORY_ROOT / "scripts" / "smoke-supabase-mcp.ps1"
DOCUMENTATION = (
    REPOSITORY_ROOT
    / "docs"
    / "development"
    / "supabase-mcp-provider"
    / "README.md"
)
SCHEMA = (
    REPOSITORY_ROOT
    / "contracts"
    / "providers"
    / "supabase"
    / "settings.schema.json"
)
PROVIDER_SOURCE = REPOSITORY_ROOT / "src" / "kis_mcp" / "providers" / "supabase"


def test_auth_script_uses_exact_interpreter_and_browser_oauth_module() -> None:
    text = AUTH_SCRIPT.read_text(encoding="utf-8")

    assert ".kis-mcp\\python-env\\Scripts\\python.exe" in text
    assert "PYTHONPATH" in text
    assert "-m kis_mcp.providers.supabase.commission" in text
    assert "projects.settings.json" in text
    assert "SUPABASE_PROJECT_REF" not in text
    assert "SUPABASE_ACCESS_TOKEN" in text
    assert "Invoke-WebRequest" not in text
    assert "Invoke-RestMethod" not in text


def test_smoke_script_supports_preflight_live_and_shared_modes() -> None:
    text = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert ".kis-mcp\\python-env\\Scripts\\python.exe" in text
    assert "PYTHONPATH" in text
    assert "-m kis_mcp.providers.supabase --check" in text
    assert "-m kis_mcp.providers.supabase.commission" in text
    assert "scripts/run-provider-live-smoke.py supabase" in text
    assert "projects.settings.json" in text
    assert "SUPABASE_PROJECT_REF" not in text
    assert "Live" in text
    assert "SharedRuntime" in text
    assert "Invoke-WebRequest" not in text
    assert "Invoke-RestMethod" not in text
    assert "curl" not in text.casefold()
    assert "npm" not in text.casefold()


def test_documentation_records_oauth_storage_scope_and_production_warning() -> None:
    text = DOCUMENTATION.read_text(encoding="utf-8")
    lowered = text.casefold()

    assert "SUPABASE_PROJECT_REF" in text
    assert "not required" in lowered
    assert "account" in lowered
    assert "project registry" in lowered
    assert "dynamic client registration" in lowered
    assert "windows credential manager" in lowered
    assert "SUPABASE_ACCESS_TOKEN" in text
    assert "legacy" in lowered
    assert "development or test" in lowered
    assert "production" in lowered
    assert "read/write" in lowered
    assert "--check" in text
    assert "get_project_url" in text
    assert "supabase_*" in text
    assert "register_provider(registry)" in text


def test_schema_is_strict_oauth_only_and_contains_no_secret_values() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    rendered = json.dumps(schema, sort_keys=True)

    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"] == {"const": 3}
    upstream = schema["properties"]["upstream"]
    authentication = schema["properties"]["authentication"]
    assert upstream["additionalProperties"] is False
    assert upstream["properties"]["base_url"] == {
        "const": "https://mcp.supabase.com/mcp"
    }
    assert upstream["properties"]["verify_tls"] == {"const": True}
    assert "access_token_env" not in rendered
    assert authentication["additionalProperties"] is False
    assert authentication["properties"]["mode"] == {"const": "oauth-dcr"}
    assert authentication["properties"]["token_storage"] == {
        "const": "windows-keyring"
    }
    assert "client_secret" not in rendered
    assert "project_ref_env" not in rendered


def test_provider_module_does_not_import_work_or_discover_boundaries() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(PROVIDER_SOURCE.glob("*.py"))
    )

    forbidden = (
        "kis_mcp.discover",
        "kis_mcp.policy",
        "kis_mcp.middleware",
        "kis_mcp.desktop_commander",
        "kis_mcp.quarantine",
        "provider_registry",
        "ThreeRuleMiddleware",
    )
    for value in forbidden:
        assert value not in source


def test_provider_has_no_custom_tool_name_allowlist() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(PROVIDER_SOURCE.glob("*.py"))
    ).casefold()

    assert "allowed_tools" not in source
    assert "tool_allowlist" not in source
    assert "filter_tools" not in source
    assert "tool_names" not in source
