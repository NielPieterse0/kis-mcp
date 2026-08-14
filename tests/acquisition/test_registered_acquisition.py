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


class FakeProjects:
    def __init__(self) -> None:
        self.items = {
            "commodity": SimpleNamespace(project_id="commodity", local_root=r"C:\Projects\commodity"),
            "import-isolate": SimpleNamespace(project_id="import-isolate", local_root=r"C:\Projects\import-isolate"),
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
        "schema_version": 1,
        "provider": {
            "project_id": "import-isolate",
            "script_relative_path": "scripts\\Invoke-RegisteredExternalAcquisition.ps1",
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
                    }
                ],
            }
        ],
    }
    path = tmp_path / "external-acquisition.settings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


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


def test_settings_are_strict_and_authorize_recipe_namespace(tmp_path: Path) -> None:
    settings = load_external_acquisition_settings(settings_file(tmp_path))
    auth = settings.authorization("commodity", "firecrawl-web")
    assert auth.recipe_directory == r"config\acquisition-recipes"
    assert auth.recipe_id_prefix == "commodity-"
    assert auth.allowed_parameter_keys == ("query",)

    bad = json.loads(settings_file(tmp_path).read_text())
    bad["provider"]["url"] = "https://example.com"
    settings_file(tmp_path).write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="unknown provider keys"):
        load_external_acquisition_settings(settings_file(tmp_path))


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
    service = RegisteredAcquisitionService(
        load_external_acquisition_settings(settings_file(tmp_path)),
        FakeProjects(),
        provider,
    )

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
    service = RegisteredAcquisitionService(
        load_external_acquisition_settings(settings_file(tmp_path)),
        FakeProjects(),
        provider,
    )

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
    service = RegisteredAcquisitionService(
        load_external_acquisition_settings(settings_file(tmp_path)),
        FakeProjects(),
        provider,
    )
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
    service = RegisteredAcquisitionService(
        load_external_acquisition_settings(settings_file(tmp_path)),
        FakeProjects(),
        provider,
    )
    with pytest.raises(ToolError, match="PROVIDER_RESULT_IDENTITY_MISMATCH"):
        service.execute(request_for(digest))
