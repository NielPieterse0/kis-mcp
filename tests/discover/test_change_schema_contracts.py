from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from kis_mcp.discover.change_contracts import ChangePathRecord
from kis_mcp.discover.change_inspection_contracts import InspectChangeRequest
from kis_mcp.discover.change_service import InspectChangeService
from kis_mcp.discover.change_targets import ChangeTargetInventory


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts" / "discover"


def _schema(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def test_request_schema_accepts_only_complete_target_shapes() -> None:
    validator = Draft202012Validator(_schema("inspect-change-request.schema.json"))

    valid = [
        {"path": r"C:\Projects\repo"},
        {"path": r"C:\Projects\repo", "source": "working_tree"},
        {"path": r"C:\Projects\repo", "source": "staged"},
        {
            "path": r"C:\Projects\repo",
            "source": "commit",
            "commit_ref": "a" * 40,
        },
        {
            "path": r"C:\Projects\repo",
            "source": "range",
            "base_ref": "main",
            "head_ref": "feature/discover",
        },
    ]
    invalid = [
        {"path": r"C:\Projects\repo", "source": "commit"},
        {
            "path": r"C:\Projects\repo",
            "source": "staged",
            "commit_ref": "a" * 40,
        },
        {
            "path": r"C:\Projects\repo",
            "source": "branch",
            "base_ref": "main",
        },
        {
            "path": r"C:\Projects\repo",
            "source": "commit",
            "commit_ref": "--output=outside",
        },
    ]

    assert all(not list(validator.iter_errors(item)) for item in valid)
    assert all(list(validator.iter_errors(item)) for item in invalid)


class _TargetReader:
    def inspect_change_target(self, request: InspectChangeRequest) -> ChangeTargetInventory:
        return ChangeTargetInventory(
            project_path=request.path,
            repository_root=request.path,
            source=request.source,
            commit_ref=request.commit_ref,
            base_ref=request.base_ref,
            head_ref=request.head_ref,
            changes=(ChangePathRecord(path="src/value.py", staged_status="modified"),),
        )


def test_general_response_schema_accepts_commit_response() -> None:
    legacy = _schema("inspect-change-working-tree-response.schema.json")
    response_schema = _schema("inspect-change-response.schema.json")
    registry = Registry().with_resource(
        "https://kis-mcp.local/contracts/discover/inspect-change-working-tree-response.schema.json",
        Resource.from_contents(legacy),
    )
    validator = Draft202012Validator(response_schema, registry=registry)
    response = InspectChangeService(_TargetReader()).inspect(
        InspectChangeRequest(
            path=r"C:\Projects\repo",
            source="commit",
            commit_ref="a" * 40,
        )
    )

    assert list(validator.iter_errors(response.to_json_dict())) == []
    assert response.change.commit_ref == "a" * 40
    assert response.source == "commit"
