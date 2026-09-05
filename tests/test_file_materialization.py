from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from kis_mcp.file_materialization import (
    FILE_MATERIALIZATION_DECLARATION,
    FILE_MATERIALIZATION_META_KEY,
    FileMaterializationPermissionTransform,
)


def _tools(server: FastMCP):
    return list(asyncio.run(server.local_provider.list_tools()))


def test_transform_declares_host_owned_default_denied_file_materialization() -> None:
    server = FastMCP("materialization-test")

    @server.tool(name="read_file")
    def read_file(path: str) -> str:
        return path

    original = _tools(server)[0]
    transformed = asyncio.run(
        FileMaterializationPermissionTransform().list_tools([original])
    )[0]
    declaration = transformed.meta[FILE_MATERIALIZATION_META_KEY]

    assert original.meta is None
    assert transformed is not original
    assert declaration == FILE_MATERIALIZATION_DECLARATION
    assert declaration["effect"] == "file_materialization"
    assert declaration["authorizationOwner"] == "host"
    assert declaration["defaultGranted"] is False


def test_transform_marks_only_tools_that_can_return_server_files() -> None:
    server = FastMCP("materialization-selection-test")

    @server.tool(name="read_multiple_files")
    def read_multiple_files(paths: list[str]) -> list[str]:
        return paths

    @server.tool(name="write_file")
    def write_file(path: str, content: str) -> str:
        return path

    transformed = asyncio.run(
        FileMaterializationPermissionTransform().list_tools(_tools(server))
    )
    by_name = {tool.name: tool for tool in transformed}

    assert FILE_MATERIALIZATION_META_KEY in by_name["read_multiple_files"].meta
    assert FILE_MATERIALIZATION_META_KEY not in (by_name["write_file"].meta or {})


def test_declared_permission_metadata_contains_no_server_grant_state() -> None:
    declaration = FILE_MATERIALIZATION_DECLARATION

    assert set(declaration) == {
        "effect",
        "authorizationOwner",
        "defaultGranted",
        "persistentGrant",
    }
    assert declaration["persistentGrant"] == "host_managed"
