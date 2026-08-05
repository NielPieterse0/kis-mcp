from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.discover.errors import DiscoverError
from kis_mcp.discover.provider_admission import (
    ProviderAdmissionBudget,
    ProviderAdmissionRequest,
    ProviderAdmissionService,
)


def _manifest(**overrides):
    value = {
        "schema_version": 1,
        "candidate_id": "provider:example",
        "name": "Example Provider",
        "provider_type": "mcp_server",
        "revision": "abc123",
        "license": None,
        "maintainer": "Example Team",
        "capabilities": ["search", "read", "search"],
        "effects": {
            "reads_project": True,
            "writes_project": True,
            "executes_commands": True,
            "network_access": True,
            "credentials": True,
        },
        "authentication": "operator_injected",
        "installation": "manual",
        "compatibility": {
            "mcp_protocol": ["2025-06-18"],
            "platforms": ["windows"],
        },
        "readiness": {
            "schema_present": True,
            "health_contract_present": False,
            "deterministic": False,
            "conformance_tests": [],
        },
        "evidence": [
            {
                "kind": "manifest",
                "path": "provider-candidate.json",
                "summary": "Checked-in provider declaration.",
            }
        ],
        "overlaps": ["discover.search"],
    }
    value.update(overrides)
    return value


def _write(root: Path, payload) -> Path:
    target = root / "provider-candidate.json"
    target.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
    return target


def _request(root: Path, **budget_overrides) -> ProviderAdmissionRequest:
    budget = {
        "max_capabilities": 20,
        "max_evidence": 20,
        "max_risks": 20,
        "max_steps": 20,
    }
    budget.update(budget_overrides)
    return ProviderAdmissionRequest(
        project=str(root),
        manifest_path="provider-candidate.json",
        budget=ProviderAdmissionBudget(**budget),
    )


def test_provider_admission_is_pending_deterministic_and_schema_valid(
    tmp_path: Path,
    discover_settings,
) -> None:
    root = tmp_path / "fixture"
    root.mkdir()
    _write(root, _manifest())
    service = ProviderAdmissionService(boundary=tmp_path, settings=discover_settings)

    first = service.inspect(_request(root))
    second = service.inspect(_request(root))

    assert first == second
    assert first.candidate.capabilities == ("read", "search")
    assert first.admission_request.decision == "pending_govern"
    assert first.admission_request.requested_effects == (
        "credentials",
        "executes_commands",
        "network_access",
        "reads_project",
        "writes_project",
    )
    assert {item.code for item in first.risks} >= {
        "CREDENTIAL_ACCESS_DECLARED",
        "EXECUTION_DECLARED",
        "LICENSE_UNRESOLVED",
        "NETWORK_ACCESS_DECLARED",
        "NONDETERMINISTIC_PROVIDER",
        "WRITE_ACCESS_DECLARED",
    }
    assert first.conformance_plan
    assert all(item.execution_available is False for item in first.conformance_plan)
    serialized = first.to_json_dict()
    forbidden_keys = {"command", "executable", "arguments"}
    stack = [serialized]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            assert forbidden_keys.isdisjoint(item)
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    assert len(first.candidate.content_digest) == 64
    assert len(first.fingerprint) == 64

    contracts = Path(__file__).parents[3] / "contracts" / "discover"
    candidate_schema = json.loads(
        (contracts / "provider-candidate.schema.json").read_text(encoding="utf-8")
    )
    admission_schema = json.loads(
        (contracts / "provider-admission-request.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(candidate_schema).validate(first.candidate.to_json_dict())
    Draft202012Validator(admission_schema).validate(
        first.admission_request.to_json_dict()
    )


def test_provider_admission_bounds_collections_and_reports_exact_omissions(
    tmp_path: Path,
    discover_settings,
) -> None:
    root = tmp_path / "bounded"
    root.mkdir()
    payload = _manifest(
        capabilities=["a", "b", "c"],
        evidence=[
            {"kind": "manifest", "path": f"evidence/{index}.json", "summary": "x"}
            for index in range(3)
        ],
    )
    _write(root, payload)

    response = ProviderAdmissionService(
        boundary=tmp_path,
        settings=discover_settings,
    ).inspect(
        _request(
            root,
            max_capabilities=2,
            max_evidence=1,
            max_risks=2,
            max_steps=2,
        )
    )

    assert response.candidate.capabilities == ("a", "b")
    assert response.omissions.capabilities == 1
    assert response.omissions.evidence == 2
    assert response.omissions.risks > 0
    assert response.omissions.steps > 0
    assert response.truncated is True
    assert set(response.truncation_reasons) == {
        "max_capabilities",
        "max_evidence",
        "max_risks",
        "max_steps",
    }


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({**_manifest(), "unexpected": True}, "DISCOVER_PROVIDER_MANIFEST_KEYS_INVALID"),
        ({**_manifest(), "schema_version": 2}, "DISCOVER_PROVIDER_MANIFEST_VERSION_UNSUPPORTED"),
        ({**_manifest(), "effects": {"network_access": True}}, "DISCOVER_PROVIDER_MANIFEST_INVALID"),
        (["not", "an", "object"], "DISCOVER_PROVIDER_MANIFEST_INVALID"),
    ],
)
def test_provider_admission_rejects_invalid_manifest_structures(
    tmp_path: Path,
    discover_settings,
    payload,
    code: str,
) -> None:
    root = tmp_path / "invalid"
    root.mkdir()
    _write(root, payload)

    with pytest.raises(DiscoverError) as raised:
        ProviderAdmissionService(boundary=tmp_path, settings=discover_settings).inspect(
            _request(root)
        )

    assert raised.value.code == code


def test_provider_admission_package_has_no_runtime_or_network_dependencies() -> None:
    package = Path(__file__).parents[3] / "src" / "kis_mcp" / "discover" / "provider_admission"
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(package.glob("*.py"))
    ).casefold()

    for forbidden in (
        "import subprocess",
        "import socket",
        "import requests",
        "import httpx",
        "import urllib",
        "from github",
        "from kis_mcp.server",
        "from kis_mcp.policy",
    ):
        assert forbidden not in source


def test_provider_admission_rejects_escaping_manifest_path(
    tmp_path: Path,
    discover_settings,
) -> None:
    root = tmp_path / "fixture"
    root.mkdir()
    (tmp_path / "outside.json").write_text("{}", encoding="utf-8")

    with pytest.raises(DiscoverError):
        ProviderAdmissionService(boundary=tmp_path, settings=discover_settings).inspect(
            ProviderAdmissionRequest(
                project=str(root),
                manifest_path="../outside.json",
                budget=ProviderAdmissionBudget(10, 10, 10, 10),
            )
        )
