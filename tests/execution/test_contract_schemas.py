from __future__ import annotations

import json
from pathlib import Path

from kis_mcp.execution.contracts import (
    EXECUTION_REQUEST_CONTRACT,
    EXECUTION_RESULT_CONTRACT,
    EXECUTION_SCHEMA_VERSION,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "contracts" / "execution"


def _schema(name: str) -> dict[str, object]:
    return json.loads((CONTRACT_ROOT / name).read_text(encoding="utf-8"))


def test_execution_request_and_result_schemas_match_public_identity() -> None:
    request = _schema("request.schema.json")
    result = _schema("result.schema.json")

    assert request["properties"]["schema_version"]["const"] == EXECUTION_SCHEMA_VERSION
    assert request["properties"]["contract"]["const"] == EXECUTION_REQUEST_CONTRACT
    assert result["properties"]["schema_version"]["const"] == EXECUTION_SCHEMA_VERSION
    assert result["properties"]["contract"]["const"] == EXECUTION_RESULT_CONTRACT


def test_execution_schema_ids_are_unique_and_settings_is_fail_closed() -> None:
    documents = [_schema(name) for name in ("request.schema.json", "result.schema.json", "settings.schema.json")]
    assert len({document["$id"] for document in documents}) == len(documents)
    settings = documents[-1]
    assert settings["additionalProperties"] is False
