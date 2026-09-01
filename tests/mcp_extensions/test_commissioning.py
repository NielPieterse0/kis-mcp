from __future__ import annotations

import asyncio

from fastmcp import FastMCP
from fastmcp.server.extensions import MethodBinding, ServerExtension
from mcp import types as mcp_types
from pydantic import BaseModel

from kis_mcp.mcp_extensions.commissioning import (
    CommissioningProfileError,
    CommissioningStep,
    McpExtensionCommissioningService,
)


class ProbeParams(mcp_types.RequestParams):
    value: int


class ProbeResult(mcp_types.Result):
    value: int


class ProbeServerExtension(ServerExtension):
    identifier = "example.test/probe"

    def settings(self):
        return {"feature": True}

    def methods(self):
        return (
            MethodBinding(
                "probe/run",
                ProbeParams,
                self._run,
                frozenset({mcp_types.LATEST_PROTOCOL_VERSION}),
            ),
        )
    async def _run(self, ctx, params):
        assert self.client_settings(ctx) == {"enabled": True}
        return ProbeResult(value=params.value + 1)


class ProbeProfile:
    profile_id = "probe"
    extension_id = "example.test/probe"

    def client_settings(self):
        return {"enabled": True}

    async def run(
        self, client, discover, *, receipt_id, server_identity_fingerprint, server
    ):
        extensions = discover.capabilities.extensions or {}
        assert extensions[self.extension_id] == {"feature": True}
        result = await client.session.send_request(
            mcp_types.Request(method="probe/run", params=ProbeParams(value=4)),
            ProbeResult,
        )
        assert result.value == 5
        assert receipt_id
        assert len(server_identity_fingerprint) == 64
        return (
            (
                CommissioningStep(
                    step="probe/run", outcome="pass", detail_code="PROBE_OK"
                ),
            ),
            {"bounded": True},
        )


class FailingProbeProfile(ProbeProfile):
    profile_id = "probe-failure"

    async def run(
        self, client, discover, *, receipt_id, server_identity_fingerprint, server
    ):
        raise CommissioningProfileError("PROBE_STABLE_FAILURE")


def test_typed_profile_failure_preserves_stable_receipt_code() -> None:
    server = FastMCP("commissioning-test")
    server.add_extension(ProbeServerExtension())
    service = McpExtensionCommissioningService(server)
    service.register_profile(FailingProbeProfile())

    receipt = asyncio.run(service.commission("probe-failure"))

    assert receipt.overall == "FAIL"
    assert receipt.steps == (
        CommissioningStep(
            step="commissioning",
            outcome="fail",
            detail_code="PROBE_STABLE_FAILURE",
        ),
    )


def test_commissioning_uses_real_in_process_dispatch_and_exact_identity() -> None:
    server = FastMCP("commissioning-test")
    server.add_extension(ProbeServerExtension())
    service = McpExtensionCommissioningService(server)
    service.register_profile(ProbeProfile())

    receipt = asyncio.run(service.commission("probe"))

    assert receipt.overall == "PASS"
    assert receipt.protocol_version == mcp_types.LATEST_PROTOCOL_VERSION
    assert receipt.extension_settings == {"enabled": True}
    assert len(receipt.server_identity_fingerprint) == 64
    assert service.receipt_matches_current(receipt) is True
def test_receipt_matching_fails_closed_on_bound_identity_drift() -> None:
    server = FastMCP("commissioning-test")
    server.add_extension(ProbeServerExtension())
    service = McpExtensionCommissioningService(server)
    service.register_profile(ProbeProfile())
    receipt = asyncio.run(service.commission("probe"))

    changed = receipt.model_copy(update={"source_revision": "f" * 40})
    assert service.receipt_matches_current(changed) is False

    changed = receipt.model_copy(update={"protocol_version": "2025-11-25"})
    assert service.receipt_matches_current(changed) is False

    changed = receipt.model_copy(update={"extension_settings_fingerprint": "0" * 64})
    assert service.receipt_matches_current(changed) is False


def test_same_named_server_instances_have_distinct_identity() -> None:
    first_server = FastMCP("commissioning-test")
    first_server.add_extension(ProbeServerExtension())
    first = McpExtensionCommissioningService(first_server)
    first.register_profile(ProbeProfile())
    receipt = asyncio.run(first.commission("probe"))

    second_server = FastMCP("commissioning-test")
    second_server.add_extension(ProbeServerExtension())
    second = McpExtensionCommissioningService(second_server)
    second.register_profile(ProbeProfile())

    assert first.server_instance_id != second.server_instance_id
    assert first.server_identity_fingerprint != second.server_identity_fingerprint
    assert second.receipt_matches_current(receipt) is False


def test_readiness_reports_only_matching_live_receipt() -> None:
    server = FastMCP("commissioning-test")
    server.add_extension(ProbeServerExtension())
    service = McpExtensionCommissioningService(server)
    service.register_profile(ProbeProfile())

    before = service.readiness("probe")
    assert before.registered is True
    assert before.last_receipt_id is None
    assert before.last_matching is False

    receipt = asyncio.run(service.commission("probe"))
    after = service.readiness("probe")
    assert after.last_receipt_id == receipt.receipt_id
    assert after.last_result == "PASS"
    assert after.last_matching is True
