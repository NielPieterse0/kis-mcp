from __future__ import annotations

import json
from pathlib import Path


SCHEMA = Path("contracts/providers/github/provider-settings.schema.json")
SETTINGS = Path("settings/providers/github-mcp.provider.json")


def test_provider_settings_schema_is_bounded_oauth_only_and_versioned() -> None:
    document = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert document["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert document["additionalProperties"] is False
    assert document["properties"]["schema_version"]["const"] == 2
    assert document["properties"]["provider_id"]["const"] == "github-mcp"
    assert document["properties"]["release_tag"]["const"] == "v1.8.0"
    assert document["properties"]["source_revision"]["const"] == "ca8ab52dcc45b86fae190398178fd22edb7b1362"
    assert document["properties"]["auth_mode"]["const"] == "oauth"
    assert "token_env" not in document["properties"]
    assert set(document["required"]) == set(document["properties"])


def test_checked_in_settings_match_the_pinned_oauth_contract() -> None:
    document = json.loads(SETTINGS.read_text(encoding="utf-8"))

    assert document["schema_version"] == 2
    assert document["release_tag"] == "v1.8.0"
    assert document["source_revision"] == "ca8ab52dcc45b86fae190398178fd22edb7b1362"
    assert document["auth_mode"] == "oauth"
    assert document["pat_env"] == "GITHUB_PERSONAL_ACCESS_TOKEN"
    assert "token_env" not in document
