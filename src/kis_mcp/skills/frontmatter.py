from __future__ import annotations

import ast
import re
from typing import Any

from .errors import SkillsError


_FRONTMATTER_KEY = re.compile(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$")


def parse_skill_frontmatter(content: str) -> dict[str, Any]:
    """Parse the conservative YAML subset accepted for SKILL.md metadata."""

    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillsError(
            "SKILLS_FRONTMATTER_INVALID",
            "SKILL.md must begin with YAML frontmatter",
        )
    closing = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing is None:
        raise SkillsError(
            "SKILLS_FRONTMATTER_INVALID", "SKILL.md frontmatter is not closed"
        )

    payload: dict[str, Any] = {}
    raw = lines[1:closing]
    index = 0
    while index < len(raw):
        line = raw[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if line[:1].isspace():
            raise SkillsError(
                "SKILLS_FRONTMATTER_INVALID", "Unexpected frontmatter indentation"
            )
        match = _FRONTMATTER_KEY.fullmatch(line)
        if match is None:
            raise SkillsError(
                "SKILLS_FRONTMATTER_INVALID", "Frontmatter entry is invalid"
            )
        key, value = match.group(1), (match.group(2) or "")
        index += 1
        if value in {"|", ">"}:
            continuation: list[str] = []
            while index < len(raw) and (
                raw[index].startswith(" ") or not raw[index].strip()
            ):
                continuation.append(raw[index].lstrip())
                index += 1
            payload[key] = (
                "\n".join(continuation).strip()
                if value == "|"
                else " ".join(item.strip() for item in continuation).strip()
            )
            continue
        if value == "":
            items: list[str] = []
            while index < len(raw) and raw[index].startswith("  - "):
                items.append(_scalar(raw[index][4:].strip()))
                index += 1
            payload[key] = items if items else ""
            continue
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            payload[key] = (
                [_scalar(item.strip()) for item in inner.split(",")] if inner else []
            )
        else:
            payload[key] = _scalar(value.strip())
    return payload


def _scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value[1:-1]
        return str(parsed)
    return value
