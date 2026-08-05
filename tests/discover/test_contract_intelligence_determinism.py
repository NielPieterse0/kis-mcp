from __future__ import annotations

from kis_mcp.discover.contract_intelligence_contracts import (
    ContractBudget,
    InspectContractsRequest,
)


def test_request_json_identity_is_deterministic() -> None:
    request = InspectContractsRequest(
        project=r"C:\Projects\example",
        budget=ContractBudget(2, 3, 4, 5),
    )
    assert request.to_json_dict() == {
        "project": r"C:\Projects\example",
        "budget": {
            "max_documents": 2,
            "max_operations": 3,
            "max_schemas": 4,
            "max_relationships": 5,
        },
    }
