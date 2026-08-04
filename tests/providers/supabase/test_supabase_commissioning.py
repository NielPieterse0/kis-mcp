from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import kis_mcp.providers.supabase.commission as commission_module
import kis_mcp.providers.supabase.smoke as smoke_module
from kis_mcp.providers.supabase.config import (
    SupabaseProviderConfig,
    load_supabase_provider_config,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONFIG = load_supabase_provider_config(REPOSITORY_ROOT)
ENVIRONMENT = {"SUPABASE_PROJECT_REF": "test-project"}
READ_WRITE_TOOLS = ["get_project_url", "list_tables", "apply_migration"]


class FakeResult:
    def __init__(
        self,
        payload: object | None,
        *,
        is_error: bool = False,
        text: str | None = None,
    ) -> None:
        self.is_error = is_error
        self.data = payload
        self.structured_content = None
        self.content = [] if text is None else [SimpleNamespace(text=text)]


class FakeClient:
    def __init__(self, *, tools: list[str], result: FakeResult) -> None:
        self._tools = tools
        self._result = result
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def list_tools(self):
        return [SimpleNamespace(name=name) for name in self._tools]

    async def call_tool(self, name: str, arguments: dict[str, object]):
        self.calls.append((name, arguments))
        return self._result


def _commission(
    client: FakeClient,
    *,
    config: SupabaseProviderConfig = CONFIG,
    tool_prefix: str = "",
) -> dict[str, bool]:
    return asyncio.run(
        commission_module.commission_supabase_client(
            client,
            config,
            ENVIRONMENT,
            tool_prefix=tool_prefix,
        )
    )


def test_commissioning_verifies_surface_and_invokes_only_harmless_read() -> None:
    client = FakeClient(
        tools=READ_WRITE_TOOLS,
        result=FakeResult({"url": "https://test-project.supabase.co"}),
    )

    report = _commission(client)

    assert client.calls == [("get_project_url", {})]
    assert report == {
        "surface": True,
        "authentication": True,
        "project_scoped_read": True,
    }
    assert "test-project" not in json.dumps(report)


def test_commissioning_uses_namespaced_surface_in_shared_runtime() -> None:
    client = FakeClient(
        tools=[f"supabase_{name}" for name in READ_WRITE_TOOLS],
        result=FakeResult({"url": "https://test-project.supabase.co"}),
    )

    report = _commission(client, tool_prefix="supabase_")

    assert client.calls == [("supabase_get_project_url", {})]
    assert report["project_scoped_read"] is True


@pytest.mark.parametrize("missing", ["get_project_url", "list_tables"])
def test_commissioning_rejects_missing_required_read_surface(missing: str) -> None:
    tools = [name for name in READ_WRITE_TOOLS if name != missing]
    client = FakeClient(tools=tools, result=FakeResult({}))

    with pytest.raises(RuntimeError, match=missing):
        _commission(client)


@pytest.mark.parametrize("account_tool", ["list_projects", "list_organizations"])
def test_commissioning_rejects_account_level_tools(account_tool: str) -> None:
    client = FakeClient(
        tools=[*READ_WRITE_TOOLS, account_tool],
        result=FakeResult({"url": "https://test-project.supabase.co"}),
    )

    with pytest.raises(RuntimeError, match="account-level tools"):
        _commission(client)


def test_commissioning_requires_non_invoked_mutation_surface_in_read_write_mode() -> None:
    client = FakeClient(
        tools=["get_project_url", "list_tables"],
        result=FakeResult({"url": "https://test-project.supabase.co"}),
    )

    with pytest.raises(RuntimeError, match="apply_migration"):
        _commission(client)


def test_commissioning_accepts_read_only_surface_without_mutating_tool() -> None:
    read_only_config = replace(CONFIG, read_only=True)
    client = FakeClient(
        tools=["get_project_url", "list_tables"],
        result=FakeResult({"url": "https://test-project.supabase.co"}),
    )

    report = _commission(client, config=read_only_config)

    assert report["project_scoped_read"] is True
    assert client.calls == [("get_project_url", {})]


def test_commissioning_rejects_mutating_tool_in_read_only_mode() -> None:
    read_only_config = replace(CONFIG, read_only=True)
    client = FakeClient(
        tools=READ_WRITE_TOOLS,
        result=FakeResult({"url": "https://test-project.supabase.co"}),
    )

    with pytest.raises(RuntimeError, match="read-only surface"):
        _commission(client, config=read_only_config)


@pytest.mark.parametrize(
    "payload",
    [
        {"url": "https://different-project.supabase.co"},
        {"url": "http://test-project.supabase.co"},
        {"url": "not-a-url"},
        {},
    ],
)
def test_commissioning_requires_exact_scoped_project_url(payload: object) -> None:
    client = FakeClient(
        tools=READ_WRITE_TOOLS,
        result=FakeResult(payload),
    )

    with pytest.raises(RuntimeError, match="project-scoped read"):
        _commission(client)


def test_commissioning_accepts_text_json_result_without_exposing_url() -> None:
    client = FakeClient(
        tools=READ_WRITE_TOOLS,
        result=FakeResult(
            None,
            text='{"url": "https://test-project.supabase.co"}',
        ),
    )

    report = _commission(client)

    assert report["project_scoped_read"] is True
    assert "test-project" not in json.dumps(report)


def test_commissioning_rejects_error_result() -> None:
    client = FakeClient(
        tools=READ_WRITE_TOOLS,
        result=FakeResult(
            {"url": "https://test-project.supabase.co"},
            is_error=True,
        ),
    )

    with pytest.raises(RuntimeError, match="project-scoped read"):
        _commission(client)


def test_standalone_commissioning_rejects_legacy_pat_before_network() -> None:
    with pytest.raises(RuntimeError, match="SUPABASE_LEGACY_PAT_CONFLICT"):
        commission_module.run_standalone_commissioning(
            CONFIG,
            environ={
                "SUPABASE_PROJECT_REF": "test-project",
                "SUPABASE_ACCESS_TOKEN": "forbidden-test-token",
            },
        )


def test_shared_runtime_status_requires_mounted_supabase() -> None:
    mounted = {
        "external_providers": [
            {
                "provider_id": "supabase",
                "mounted": True,
                "state": "mounted",
            }
        ]
    }
    not_mounted = {
        "external_providers": [
            {
                "provider_id": "supabase",
                "mounted": False,
                "state": "build_failed",
            }
        ]
    }

    assert smoke_module._supabase_mounted(mounted) is True
    assert smoke_module._supabase_mounted(not_mounted) is False
