from __future__ import annotations

from collections.abc import Sequence
from copy import copy
from typing import Any

from fastmcp.server.transforms import Transform

FILE_MATERIALIZATION_META_KEY = "com.nielpieterse.kis/fileMaterialization"
FILE_MATERIALIZATION_EFFECT = "file_materialization"
FILE_MATERIALIZING_TOOLS = frozenset({"read_file", "read_multiple_files"})

FILE_MATERIALIZATION_DECLARATION = {
    "effect": FILE_MATERIALIZATION_EFFECT,
    "authorizationOwner": "host",
    "defaultGranted": False,
    "persistentGrant": "host_managed",
}


def _with_materialization_metadata(tool: Any) -> Any:
    if str(getattr(tool, "name", "")) not in FILE_MATERIALIZING_TOOLS:
        return tool
    meta = dict(getattr(tool, "meta", None) or {})
    meta[FILE_MATERIALIZATION_META_KEY] = dict(FILE_MATERIALIZATION_DECLARATION)
    model_copy = getattr(tool, "model_copy", None)
    if callable(model_copy):
        return model_copy(update={"meta": meta})
    cloned = copy(tool)
    setattr(cloned, "meta", meta)
    return cloned


class FileMaterializationPermissionTransform(Transform):
    """Declare host-owned file materialization permission without authorizing it."""

    async def list_tools(self, tools: Sequence[Any]) -> Sequence[Any]:
        return [_with_materialization_metadata(tool) for tool in tools]


__all__ = [
    "FILE_MATERIALIZATION_DECLARATION",
    "FILE_MATERIALIZATION_EFFECT",
    "FILE_MATERIALIZATION_META_KEY",
    "FILE_MATERIALIZING_TOOLS",
    "FileMaterializationPermissionTransform",
]
