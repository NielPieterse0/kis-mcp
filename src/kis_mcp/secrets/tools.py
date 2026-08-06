from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from .service import SecretsService


SECRETS_TOOL_NAMES = (
    "kis_secret_status",
    "kis_list_secret_references",
    "kis_lock_secrets",
)


def register_secret_tools(
    server: FastMCP,
    service: SecretsService,
) -> SecretsService:
    """Register metadata-only secret operations; never expose plaintext."""

    @server.tool(
        name="kis_secret_status",
        description="Return encrypted-vault initialization and lock metadata only.",
    )
    def kis_secret_status() -> dict[str, Any]:
        return service.status().to_dict()

    @server.tool(
        name="kis_list_secret_references",
        description="List canonical secret references and update timestamps only.",
    )
    def kis_list_secret_references() -> dict[str, Any]:
        return {
            "schema_version": 1,
            "references": [
                record.to_dict() for record in service.list_references()
            ],
        }

    @server.tool(
        name="kis_lock_secrets",
        description="Clear the in-memory session key and return lock metadata.",
    )
    def kis_lock_secrets() -> dict[str, Any]:
        service.lock()
        return service.status().to_dict()

    return service
