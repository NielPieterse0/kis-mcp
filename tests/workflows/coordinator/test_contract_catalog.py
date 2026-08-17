from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).parents[3]
CONTRACT_ROOT = ROOT / "contracts" / "coordinator"
EXPECTED_CONTRACTS = (
    "coordinator-state",
    "dependency-dag",
    "lease",
    "reconciliation-result",
    "reservation",
    "runtime-binding",
    "scope-revision",
    "verification-requirements",
    "work-packet",
    "worker-execution",
    "worker-handoff",
)


def _schema(name: str) -> dict[str, object]:
    return json.loads(
        (CONTRACT_ROOT / f"{name}.schema.json").read_text(encoding="utf-8")
    )


def test_contract_directory_exposes_exact_current_contracts() -> None:
    names = tuple(sorted(path.stem.removesuffix(".schema") for path in CONTRACT_ROOT.glob("*.schema.json")))
    assert names == EXPECTED_CONTRACTS


def test_every_contract_is_strict_valid_draft_2020_12() -> None:
    for name in EXPECTED_CONTRACTS:
        schema = _schema(name)
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == (
            f"https://kis-mcp.local/contracts/coordinator/{name}.schema.json"
        )
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False


def test_slice_five_runtime_surface_stops_before_reconciliation_and_telemetry() -> None:
    package = ROOT / "src" / "kis_mcp" / "workflows" / "coordinator"
    assert package.is_dir()
    assert {path.name for path in package.glob("*.py")} == {
        "__init__.py",
        "adapters.py",
        "authority.py",
        "models.py",
        "planner.py",
        "service.py",
        "worker.py",
    }
    for deferred in ("reconciliation", "telemetry"):
        assert not (package / f"{deferred}.py").exists()
