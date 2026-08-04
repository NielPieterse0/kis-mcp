from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
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


def test_smoke_script_uses_exact_project_interpreter_and_non_network_check() -> None:
    text = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert ".kis-mcp\\python-env\\Scripts\\python.exe" in text
    assert "-m kis_mcp.providers.supabase --check" in text
    assert "Invoke-WebRequest" not in text
    assert "Invoke-RestMethod" not in text
    assert "curl" not in text.casefold()
    assert "npm" not in text.casefold()


def test_documentation_records_scope_credentials_and_production_warning() -> None:
    text = DOCUMENTATION.read_text(encoding="utf-8")

    assert "SUPABASE_PROJECT_REF" in text
    assert "SUPABASE_ACCESS_TOKEN" in text
    assert "development or test" in text.casefold()
    assert "production" in text.casefold()
    assert "read/write" in text.casefold()
    assert "--check" in text
    assert "provider_registry.py" in text


def test_schema_is_strict_and_contains_no_secret_values() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    rendered = json.dumps(schema, sort_keys=True)

    assert schema["additionalProperties"] is False
    upstream = schema["properties"]["upstream"]
    assert upstream["additionalProperties"] is False
    assert upstream["properties"]["base_url"] == {
        "const": "https://mcp.supabase.com/mcp"
    }
    assert upstream["properties"]["verify_tls"] == {"const": True}
    assert "access_token_env" in rendered
    assert "access_token\"" not in rendered
    assert "project_ref_env" in rendered


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
