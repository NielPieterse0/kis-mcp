from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastmcp.exceptions import ToolError

from kis_mcp.acquisition import service as service_module
from kis_mcp.acquisition.service import RegisteredAcquisitionService
from kis_mcp.acquisition.settings import load_external_acquisition_settings


FIRECRAWL_PROFILE = {
    "schema_version": 1,
    "profile_id": "firecrawl-web",
    "purpose": "Acquire bounded web information through the Firecrawl MCP provider.",
    "network_mode": "external",
    "input_mode": "none",
    "output_scope": "staging",
    "credentials": ["FIRECRAWL_API_KEY"],
    "allowed_tools": ["firecrawl_map", "firecrawl_scrape", "firecrawl_search"],
    "denied_tools": [
        "firecrawl_agent",
        "firecrawl_crawl",
        "firecrawl_developer",
        "firecrawl_extract",
        "firecrawl_interact",
        "firecrawl_monitor",
        "firecrawl_parse",
        "firecrawl_research",
    ],
}


def profile_hash(profile: dict[str, object]) -> str:
    canonical = json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_provider_policy(tmp_path: Path, profiles: list[dict[str, object]] | None = None) -> Path:
    root = tmp_path / "import-isolate"
    policy = root / "policy" / "provider-profiles.json"
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(
        json.dumps({"schema_version": 3, "profiles": profiles if profiles is not None else [FIRECRAWL_PROFILE]}),
        encoding="utf-8",
    )
    return root


class FakeProjects:
    def __init__(self, provider_root: str = r"C:\Projects\import-isolate") -> None:
        self.items = {
            "commodity": SimpleNamespace(project_id="commodity", local_root=r"C:\Projects\commodity"),
            "import-isolate": SimpleNamespace(project_id="import-isolate", local_root=provider_root),
        }

    def project(self, project_id: str):
        if project_id not in self.items:
            raise KeyError(project_id)
        return self.items[project_id]


class FakeProvider:
    def __init__(self, result: dict[str, object] | None = None) -> None:
        self.calls: list[tuple[dict[str, object], str]] = []
        self.result = result

    def acquire(self, request: dict[str, object], recipe_path: str) -> dict[str, object]:
        self.calls.append((dict(request), recipe_path))
        if self.result is not None:
            return dict(self.result)
        return {
            "schema_version": 1,
            "provider": "import-isolate",
            "provider_type": "firecrawl-mcp",
            "project_id": request["project_id"],
            "profile_id": request["profile_id"],
            "recipe_id": request["recipe_id"],
            "recipe_hash": request["recipe_hash"],
            "content_class": "web-evidence",
            "artifact_sha256": "sha256:" + "a" * 64,
            "byte_count": 123,
            "artifact_relative_path": "staging/run/web-intake.json",
            "provider_implementation_revision": "sha256:" + "b" * 64,
            "container_image_digest": "sha256:" + "c" * 64,
            "credential_references": ["FIRECRAWL_API_KEY"],
            "state": "success",
            "failure_code": None,
        }


def settings_file(tmp_path: Path) -> Path:
    payload = {
        "schema_version": 2,
        "provider": {
            "project_id": "import-isolate",
            "script_relative_path": "scripts\\Invoke-RegisteredExternalAcquisition.ps1",
            "profile_policy_relative_path": "policy\\provider-profiles.json",
        },
        "limits": {
            "max_parameters": 16,
            "max_parameter_string_chars": 1024,
            "max_request_json_chars": 16384,
        },
        "authorizations": [
            {
                "project_id": "commodity",
                "profiles": [
                    {
                        "profile_id": "firecrawl-web",
                        "approval_required": True,
                        "recipe_directory": "config\\acquisition-recipes",
                        "recipe_id_prefix": "commodity-",
                        "allowed_parameter_keys": ["query"],
                        "request_schema_version": 1,
                        "provider_profile_schema_version": 1,
                        "provider_profile_sha256": profile_hash(FIRECRAWL_PROFILE),
                    }
                ],
            }
        ],
    }
    path = tmp_path / "external-acquisition.settings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def acquisition_service(tmp_path: Path, provider: FakeProvider) -> RegisteredAcquisitionService:
    provider_root = write_provider_policy(tmp_path)
    return RegisteredAcquisitionService(
        load_external_acquisition_settings(settings_file(tmp_path)),
        FakeProjects(str(provider_root)),
        provider,
    )


def request_for(recipe_hash: str, **overrides: object) -> dict[str, object]:
    request: dict[str, object] = {
        "project": "commodity",
        "profile": "firecrawl-web",
        "recipe": "commodity-news-search",
        "recipe_hash": recipe_hash,
        "parameters": {"query": "natural gas storage news"},
        "approved": True,
    }
    request.update(overrides)
    return request


def generic_profile(*, enabled: bool = True) -> dict[str, object]:
    return {
        "schema_version": 3,
        "profile_id": "commodity-generic-http",
        "purpose": "Commodity bounded generic HTTP fixture",
        "provider_type": "http",
        "content_class": "data-evidence",
        "enabled": enabled,
        "network_mode": "external",
        "input_mode": "none",
        "output_scope": "staging",
        "credentials": [],
        "allowed_tools": ["raw-http"],
        "denied_tools": [],
    }


def generic_settings_file(tmp_path: Path, profile: dict[str, object]) -> Path:
    path = settings_file(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    authorization = payload["authorizations"][0]["profiles"][0]
    authorization.update(
        {
            "profile_id": "commodity-generic-http",
            "allowed_parameter_keys": ["dates"],
            "request_schema_version": 2,
            "provider_profile_schema_version": 3,
            "provider_profile_sha256": profile_hash(profile),
        }
    )
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_settings_are_strict_and_authorize_recipe_namespace(tmp_path: Path) -> None:
    path = settings_file(tmp_path)
    settings = load_external_acquisition_settings(path)
    auth = settings.authorization("commodity", "firecrawl-web")
    assert auth.recipe_directory == r"config\acquisition-recipes"
    assert auth.recipe_id_prefix == "commodity-"
    assert auth.allowed_parameter_keys == ("query",)
    assert auth.request_schema_version == 1
    assert auth.provider_profile_schema_version == 1
    assert auth.provider_profile_sha256 == profile_hash(FIRECRAWL_PROFILE)
    assert settings.provider_profile_policy_relative_path == r"policy\provider-profiles.json"

    bad = json.loads(path.read_text())
    bad["provider"]["url"] = "https://example.com"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="unknown provider keys"):
        load_external_acquisition_settings(path)

    legacy = json.loads(settings_file(tmp_path).read_text())
    legacy["schema_version"] = 1
    path.write_text(json.dumps(legacy))
    with pytest.raises(ValueError, match="schema_version must be 2"):
        load_external_acquisition_settings(path)


def test_authorized_request_hashes_registered_consumer_recipe_before_provider_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recipe_bytes = b'{"schema_version":2,"recipe_id":"commodity-news-search"}'
    digest = "sha256:" + hashlib.sha256(recipe_bytes).hexdigest()
    monkeypatch.setattr(
        service_module,
        "_read_recipe",
        lambda root, directory, recipe: (r"C:\Projects\commodity\config\acquisition-recipes\commodity-news-search.json", recipe_bytes),
    )
    provider = FakeProvider()
    service = acquisition_service(tmp_path, provider)

    result = service.execute(request_for(digest))

    assert result["state"] == "success"
    assert len(provider.calls) == 1
    provider_request, recipe_path = provider.calls[0]
    assert provider_request == {
        "schema_version": 1,
        "project_id": "commodity",
        "profile_id": "firecrawl-web",
        "recipe_id": "commodity-news-search",
        "recipe_hash": digest,
        "parameters": {"query": "natural gas storage news"},
    }
    assert recipe_path.endswith("commodity-news-search.json")
    assert "approved" not in provider_request


def test_unregistered_or_unauthorized_requests_fail_before_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recipe_bytes = b"{}"
    digest = "sha256:" + hashlib.sha256(recipe_bytes).hexdigest()
    monkeypatch.setattr(service_module, "_read_recipe", lambda *args: ("recipe.json", recipe_bytes))
    provider = FakeProvider()
    service = acquisition_service(tmp_path, provider)

    cases = [
        request_for(digest, project="unknown"),
        request_for(digest, profile="public-http-dataset"),
        request_for(digest, recipe="other-news-search"),
        request_for(digest, parameters={"url": "https://example.com"}),
        request_for(digest, approved=False),
    ]
    for request in cases:
        with pytest.raises(ToolError):
            service.execute(request)
    assert provider.calls == []


def test_recipe_hash_mismatch_fails_before_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service_module, "_read_recipe", lambda *args: ("recipe.json", b"actual"))
    provider = FakeProvider()
    service = acquisition_service(tmp_path, provider)
    with pytest.raises(ToolError, match="RECIPE_HASH_MISMATCH"):
        service.execute(request_for("sha256:" + "0" * 64))
    assert provider.calls == []


def test_provider_result_identity_mismatch_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recipe_bytes = b"{}"
    digest = "sha256:" + hashlib.sha256(recipe_bytes).hexdigest()
    monkeypatch.setattr(service_module, "_read_recipe", lambda *args: ("recipe.json", recipe_bytes))
    provider = FakeProvider(
        {
            "schema_version": 1,
            "provider": "import-isolate",
            "provider_type": "firecrawl-mcp",
            "project_id": "some-other-project",
            "profile_id": "firecrawl-web",
            "recipe_id": "commodity-news-search",
            "recipe_hash": digest,
            "content_class": "web-evidence",
            "artifact_sha256": "sha256:" + "a" * 64,
            "byte_count": 1,
            "artifact_relative_path": "staging/run/web-intake.json",
            "provider_implementation_revision": "sha256:" + "b" * 64,
            "container_image_digest": "sha256:" + "c" * 64,
            "credential_references": ["FIRECRAWL_API_KEY"],
            "state": "success",
            "failure_code": None,
        }
    )
    service = acquisition_service(tmp_path, provider)
    with pytest.raises(ToolError, match="PROVIDER_RESULT_IDENTITY_MISMATCH"):
        service.execute(request_for(digest))


def test_request_v2_preserves_bounded_list_parameters_after_exact_profile_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recipe_bytes = b'{"schema_version":3,"recipe_id":"commodity-news-search"}'
    digest = "sha256:" + hashlib.sha256(recipe_bytes).hexdigest()
    monkeypatch.setattr(service_module, "_read_recipe", lambda *args: ("recipe.json", recipe_bytes))
    profile = generic_profile()
    provider_root = write_provider_policy(tmp_path, [profile])
    provider = FakeProvider()
    service = RegisteredAcquisitionService(
        load_external_acquisition_settings(generic_settings_file(tmp_path, profile)),
        FakeProjects(str(provider_root)),
        provider,
    )

    service.execute(
        request_for(
            digest,
            profile="commodity-generic-http",
            parameters={"dates": ["2026-08-01", "2026-08-02"]},
        )
    )

    provider_request, _ = provider.calls[0]
    assert provider_request["schema_version"] == 2
    assert provider_request["parameters"] == {"dates": ["2026-08-01", "2026-08-02"]}


def test_profile_drift_or_ambiguity_fails_before_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recipe_bytes = b"{}"
    digest = "sha256:" + hashlib.sha256(recipe_bytes).hexdigest()
    monkeypatch.setattr(service_module, "_read_recipe", lambda *args: ("recipe.json", recipe_bytes))
    expected = generic_profile()

    cases = [
        [dict(expected, purpose="changed")],
        [dict(expected, schema_version=2)],
        [dict(expected, enabled=False)],
        [expected, dict(expected)],
        [dict(expected, profile_id="other-profile")],
    ]
    for index, profiles in enumerate(cases):
        case_root = tmp_path / f"case-{index}"
        provider_root = write_provider_policy(case_root, profiles)
        provider = FakeProvider()
        service = RegisteredAcquisitionService(
            load_external_acquisition_settings(generic_settings_file(case_root, expected)),
            FakeProjects(str(provider_root)),
            provider,
        )
        with pytest.raises(ToolError, match="PROVIDER_PROFILE"):
            service.execute(
                request_for(
                    digest,
                    profile="commodity-generic-http",
                    parameters={"dates": ["2026-08-01"]},
                )
            )
        assert provider.calls == []


def test_request_versions_keep_list_authority_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recipe_bytes = b"{}"
    digest = "sha256:" + hashlib.sha256(recipe_bytes).hexdigest()
    monkeypatch.setattr(service_module, "_read_recipe", lambda *args: ("recipe.json", recipe_bytes))

    v1_provider = FakeProvider()
    v1_service = acquisition_service(tmp_path / "v1", v1_provider)
    with pytest.raises(ToolError, match="parameter query"):
        v1_service.execute(request_for(digest, parameters={"query": ["one", "two"]}))
    assert v1_provider.calls == []

    profile = generic_profile()
    provider_root = write_provider_policy(tmp_path / "v2", [profile])
    v2_provider = FakeProvider()
    v2_service = RegisteredAcquisitionService(
        load_external_acquisition_settings(generic_settings_file(tmp_path / "v2", profile)),
        FakeProjects(str(provider_root)),
        v2_provider,
    )
    with pytest.raises(ToolError, match="parameter dates"):
        v2_service.execute(
            request_for(
                digest,
                profile="commodity-generic-http",
                parameters={"dates": [str(index) for index in range(65)]},
            )
        )
    assert v2_provider.calls == []
