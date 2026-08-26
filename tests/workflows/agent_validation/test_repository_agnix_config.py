from __future__ import annotations

import json
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / ".agnix.toml"
MCP_SCHEMA = ROOT / "contracts" / "tools" / "mcp-sdk-integrations" / "mcp-spec.schema.json"


def test_repository_agnix_config_excludes_only_non_agent_mcp_schema() -> None:
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))

    assert config == {
        "exclude": ["contracts/tools/mcp-sdk-integrations/mcp-spec.schema.json"],
        "spec_revisions": {"mcp_protocol": "2026-07-28"},
    }


def test_excluded_contract_is_json_schema_not_agent_mcp_configuration() -> None:
    schema = json.loads(MCP_SCHEMA.read_text(encoding="utf-8"))

    assert schema["$schema"].startswith("https://json-schema.org/")
    assert "properties" in schema
    assert "AGENTS.md" not in CONFIG.read_text(encoding="utf-8")
