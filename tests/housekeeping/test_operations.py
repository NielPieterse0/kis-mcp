from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from kis_mcp.housekeeping.operations import FastMCPInvoker


def _result(payload: dict) -> SimpleNamespace:
    return SimpleNamespace(is_error=False, content=(), structured_content=payload)


def _text_result(text: str, *, extra_content: bool = False) -> SimpleNamespace:
    content = [SimpleNamespace(text=text)]
    if extra_content:
        content.append(SimpleNamespace(text="second"))
    return SimpleNamespace(is_error=False, content=tuple(content), structured_content=None)


def _budget_envelope(operation: str) -> dict:
    return {
        "truncated": True,
        "reason": "RESULT_BUDGET_EXCEEDED",
        "operation": operation,
        "original_chars": 2000,
        "max_chars": 1000,
        "preview": {"items": {"omitted_items": 100}},
    }


def test_read_recovers_payload_after_dispatch_result_budget_truncation() -> None:
    calls: list[tuple[str, dict, dict]] = []

    class Server:
        async def call_tool(self, name, arguments, **kwargs):
            calls.append((name, arguments, kwargs))
            if name == "execute_read_action":
                return _result(_budget_envelope("project_management_inventory"))
            assert name == "project_management_inventory"
            return _result({"items": [{"item_id": "1"}], "truncated": False})

    payload = asyncio.run(
        FastMCPInvoker(Server()).read(
            "project_management_inventory", {"project_id": "kis-mcp"}
        )
    )

    assert payload == {"items": [{"item_id": "1"}], "truncated": False}
    assert calls == [
        (
            "execute_read_action",
            {
                "operation": "project_management_inventory",
                "arguments": {"project_id": "kis-mcp"},
            },
            {},
        ),
        (
            "project_management_inventory",
            {"project_id": "kis-mcp"},
            {"run_middleware": True},
        ),
    ]


@pytest.mark.parametrize(
    ("method_name", "surface"),
    [
        ("change", "execute_change_action"),
        ("external", "execute_external_action"),
    ],
)
def test_mutating_calls_do_not_replay_budget_truncated_results(
    method_name: str,
    surface: str,
) -> None:
    calls: list[str] = []

    class Server:
        async def call_tool(self, name, arguments, **kwargs):
            calls.append(name)
            return _result(_budget_envelope("example_operation"))

    invoker = FastMCPInvoker(Server())
    method = getattr(invoker, method_name)
    with pytest.raises(RuntimeError, match="RESULT_BUDGET_EXCEEDED"):
        asyncio.run(method("example_operation", {"apply": True}))

    assert calls == [surface]


def test_read_does_not_replay_domain_payload_with_budget_reason_only() -> None:
    calls: list[str] = []
    domain_payload = {
        "truncated": True,
        "reason": "RESULT_BUDGET_EXCEEDED",
        "operation": "project_management_inventory",
        "items": [],
    }

    class Server:
        async def call_tool(self, name, arguments, **kwargs):
            calls.append(name)
            if name != "execute_read_action":
                raise AssertionError("domain payload must not trigger replay")
            return _result(domain_payload)

    payload = asyncio.run(
        FastMCPInvoker(Server()).read(
            "project_management_inventory", {"project_id": "kis-mcp"}
        )
    )

    assert payload == domain_payload
    assert calls == ["execute_read_action"]


def test_external_accepts_single_text_only_tool_result_without_replay() -> None:
    calls: list[tuple[str, dict]] = []

    class Server:
        async def call_tool(self, name, arguments, **kwargs):
            calls.append((name, arguments))
            assert kwargs == {}
            return _text_result('{"state":"closed"}')

    payload = asyncio.run(
        FastMCPInvoker(Server()).external(
            "github_issue_read", {"method": "get", "issue_number": 251}
        )
    )

    assert payload == {"text": '{"state":"closed"}'}
    assert calls == [
        (
            "execute_external_action",
            {
                "operation": "github_issue_read",
                "arguments": {"method": "get", "issue_number": 251},
            },
        )
    ]


def test_text_only_tool_result_fails_closed_when_content_is_ambiguous() -> None:
    class Server:
        async def call_tool(self, _name, _arguments, **_kwargs):
            return _text_result('{"state":"closed"}', extra_content=True)

    with pytest.raises(RuntimeError, match="no structured content"):
        asyncio.run(
            FastMCPInvoker(Server()).external(
                "github_issue_read", {"method": "get", "issue_number": 251}
            )
        )


def test_text_fallback_rejects_malformed_present_structured_content() -> None:
    class Server:
        async def call_tool(self, _name, _arguments, **_kwargs):
            return SimpleNamespace(
                is_error=False,
                content=(SimpleNamespace(text='{"state":"closed"}'),),
                structured_content=["malformed"],
            )

    with pytest.raises(RuntimeError, match="invalid structured content"):
        asyncio.run(
            FastMCPInvoker(Server()).external(
                "github_issue_read", {"method": "get", "issue_number": 251}
            )
        )
