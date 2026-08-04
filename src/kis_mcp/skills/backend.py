from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from .errors import SkillsError


class SkillsWorkBackend(Protocol):
    """Narrow mutation port implemented by the existing Work backend."""

    async def create_directory(self, path: str) -> None: ...

    async def write_text(self, path: str, content: str) -> None: ...

    async def move(self, source: str, destination: str) -> None: ...

    async def replace_text(
        self, path: str, old_string: str, new_string: str
    ) -> None: ...


class FastMcpWorkBackend:
    """Re-enter the kis-mcp server so normal middleware governs mutations."""

    def __init__(self, server: Any) -> None:
        self._server = server

    async def create_directory(self, path: str) -> None:
        await self._call("create_directory", {"path": path})

    async def write_text(self, path: str, content: str) -> None:
        await self._call(
            "write_file",
            {
                "path": path,
                "content": content,
                "mode": "rewrite",
                "origin": "llm",
            },
        )

    async def move(self, source: str, destination: str) -> None:
        await self._call(
            "move_file", {"source": source, "destination": destination}
        )

    async def replace_text(
        self, path: str, old_string: str, new_string: str
    ) -> None:
        await self._call(
            "edit_block",
            {
                "file_path": path,
                "old_string": old_string,
                "new_string": new_string,
                "expected_replacements": 1,
                "origin": "llm",
            },
        )

    async def _call(self, name: str, arguments: Mapping[str, object]) -> None:
        try:
            result = await self._server.call_tool(
                name, dict(arguments), run_middleware=True
            )
        except Exception as exc:
            raise SkillsError(
                "SKILLS_BACKEND_FAILED",
                f"Work backend operation {name} failed: {exc}",
                subject=name,
            ) from exc
        if getattr(result, "is_error", False):
            detail = self._result_text(result) or "provider returned an error"
            raise SkillsError(
                "SKILLS_BACKEND_FAILED",
                f"Work backend operation {name} failed: {detail}",
                subject=name,
            )

    @staticmethod
    def _result_text(result: Any) -> str:
        parts: list[str] = []
        for item in getattr(result, "content", ()) or ():
            text = getattr(item, "text", None)
            if isinstance(text, str) and text:
                parts.append(text)
        return "; ".join(parts)
