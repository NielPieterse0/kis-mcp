from __future__ import annotations

import json
from pathlib import Path


SCHEMA = Path("contracts/providers/github/provider-settings.schema.json")


def test_provider_settings_schema_is_bounded_and_versioned() -> None:
    document = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert document["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert document["additionalProperties"] is False
    assert document["properties"]["schema_version"]["const"] == 1
    assert document["properties"]["provider_id"]["const"] == "github-mcp"
    assert set(document["required"]) == set(document["properties"])
