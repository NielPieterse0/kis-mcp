from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.commissioning.settings import (
    PostMergeCommissioningSettings,
    load_post_merge_commissioning_settings,
)
from kis_mcp.config import RuntimeConfig

from .invoker import CommissioningFastMCPInvoker
from .processor import CommissioningCandidateProcessor
from .provider import CommissioningLifecycleProvider, normalized_runtime_instance
from .runner import CommissioningRunnerService
from .service import CommissioningRuntimeService
from .state import CommissioningStateStore


def register_commissioning_tools(
    server: FastMCP,
    service: CommissioningRuntimeService,
    runner: CommissioningRunnerService,
) -> None:
    @server.tool
    def kis_post_merge_commissioning_status() -> dict:
        """Read post-merge commissioning observer/checkpoint status."""
        return service.status()

    @server.tool
    def kis_post_merge_commissioning_receipt(receipt_id: str) -> dict:
        """Read one persisted post-merge commissioning observer receipt."""
        try:
            return service.receipt(receipt_id)
        except (KeyError, ValueError) as exc:
            raise ToolError(
                f"POST_MERGE_COMMISSIONING_RECEIPT_NOT_FOUND: {receipt_id}"
            ) from exc

    @server.tool
    def kis_post_merge_commissioning_execution(commissioning_key: str) -> dict:
        """Read one bounded commissioning execution state and proof receipt."""
        try:
            return runner.execution(commissioning_key)
        except (KeyError, ValueError) as exc:
            raise ToolError(
                f"POST_MERGE_COMMISSIONING_EXECUTION_NOT_FOUND: {commissioning_key}"
            ) from exc

    @server.tool
    async def kis_post_merge_commissioning_run(
        repository: str,
        commissioning_issue: int,
        execution_owner: str,
        retry: bool = False,
    ) -> dict:
        """Execute one claimed deterministic commissioning obligation."""
        try:
            return await runner.run(
                repository,
                commissioning_issue,
                execution_owner=execution_owner,
                retry=retry,
            )
        except (KeyError, RuntimeError, ValueError) as exc:
            raise ToolError(f"POST_MERGE_COMMISSIONING_RUN_REJECTED: {exc}") from exc


def compose_post_merge_commissioning_runtime(
    server: FastMCP,
    runtime: RuntimeConfig,
    *,
    environment: Mapping[str, str] | None = None,
    settings: PostMergeCommissioningSettings | None = None,
) -> CommissioningRuntimeService:
    selected = settings or load_post_merge_commissioning_settings()
    state_root = Path(runtime.state_root) / selected.state_namespace
    store = CommissioningStateStore(
        state_root,
        retention=selected.receipt_retention,
    )
    invoker = CommissioningFastMCPInvoker(server)
    service = CommissioningRuntimeService(
        selected,
        store,
        invoker=invoker,
        processor=CommissioningCandidateProcessor(selected),
        current_instance=normalized_runtime_instance(environment),
    )
    runner = CommissioningRunnerService(
        selected,
        store,
        invoker=invoker,
    )
    server.add_provider(CommissioningLifecycleProvider(service))
    register_commissioning_tools(server, service, runner)
    return service


__all__ = [
    "compose_post_merge_commissioning_runtime",
    "register_commissioning_tools",
]
