from __future__ import annotations

from kis_mcp.discover.impact_contracts import ImpactBudget, InspectImpactRequest


def test_request_path_order_and_identity_are_stable() -> None:
    request = InspectImpactRequest(
        project=r"C:\Projects\example",
        changed_paths=("src/b.py", "src/a.py", "src/b.py"),
        budget=ImpactBudget(1, 2, 3, 4),
    )
    assert request.changed_paths == ("src/b.py", "src/a.py")
    assert request.to_json_dict() == {
        "project": r"C:\Projects\example",
        "changed_paths": ["src/b.py", "src/a.py"],
        "budget": {
            "max_symbols": 1,
            "max_dependants": 2,
            "max_tests": 3,
            "max_verifications": 4,
        },
    }
