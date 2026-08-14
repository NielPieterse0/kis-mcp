from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastmcp.exceptions import ToolError

from kis_mcp.acquisition.provider import ImportIsolateProvider


def request() -> dict[str, object]:
    return {
        "schema_version": 1,
        "project_id": "commodity",
        "profile_id": "firecrawl-web",
        "recipe_id": "commodity-news-search",
        "recipe_hash": "sha256:" + "0" * 64,
        "parameters": {"query": "natural gas news"},
    }


def test_failed_provider_does_not_reflect_child_output(tmp_path: Path) -> None:
    def runner(args, cwd, env):
        return SimpleNamespace(
            returncode=2,
            stdout="diagnostic query value",
            stderr="FIRECRAWL_API_KEY=supersecret",
        )

    provider = ImportIsolateProvider(
        r"C:\Projects\import-isolate",
        r"scripts\Invoke-RegisteredExternalAcquisition.ps1",
        str(tmp_path),
        runner=runner,
    )

    with pytest.raises(ToolError) as excinfo:
        provider.acquire(request(), r"C:\Projects\commodity\config\acquisition-recipes\commodity-news-search.json")

    message = str(excinfo.value)
    assert "supersecret" not in message
    assert "FIRECRAWL_API_KEY" not in message
    assert "diagnostic query value" not in message
    assert "IMPORT_ISOLATE_ACQUISITION_FAILED" in message


def test_success_uses_only_final_json_result_line(tmp_path: Path) -> None:
    payload = {
        "schema_version": 1,
        "provider": "import-isolate",
        "state": "success",
    }

    def runner(args, cwd, env):
        return SimpleNamespace(
            returncode=0,
            stdout="provider build diagnostic\n" + json.dumps(payload),
            stderr="",
        )

    provider = ImportIsolateProvider(
        r"C:\Projects\import-isolate",
        r"scripts\Invoke-RegisteredExternalAcquisition.ps1",
        str(tmp_path),
        runner=runner,
    )

    assert provider.acquire(request(), r"C:\Projects\commodity\config\acquisition-recipes\commodity-news-search.json") == payload
