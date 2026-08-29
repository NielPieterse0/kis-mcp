from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from typing import Any

from .state import TaskHandoffStore

IssueLoader = Callable[[str, str, int], Awaitable[dict[str, Any]]]


def _section(body: str, heading: str) -> str:
    match = re.search(
        rf"(?ims)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)",
        body,
    )
    return match.group(1).strip() if match else ""


def _bullets(text: str) -> tuple[str, ...]:
    values = tuple(
        match.group(1).strip()
        for line in text.splitlines()
        if (match := re.match(r"^\s*[-*]\s+(.+?)\s*$", line))
    )
    return tuple(item for item in values if item)


def _surfaces(title: str, body: str) -> tuple[str, ...]:
    text = f"{title}\n{body}".casefold()
    values: list[str] = []
    if "mcp" in text:
        values.append("mcp")
    if "work" in text or "project" in text:
        values.append("work_management")
    if "github" in text or "provider" in text or "pull request" in text:
        values.append("provider")
    if not values:
        values.append("repository")
    return tuple(values)


class WorkActivationCoordinator:
    def __init__(self, store: TaskHandoffStore, issue_loader: IssueLoader) -> None:
        self._store = store
        self._issue_loader = issue_loader

    async def materialize(
        self,
        project_id: str,
        repository: str,
        issue_number: int,
    ) -> dict[str, Any]:
        if "/" not in repository:
            raise ValueError("WORK_ACTIVATION_REPOSITORY_INVALID")
        issue = await self._issue_loader(*repository.split("/", 1), issue_number)
        title = str(issue.get("title", "")).strip()
        body = str(issue.get("body", ""))
        outcome = _section(body, "Outcome")
        scope = _bullets(_section(body, "Scope"))
        criteria = _bullets(_section(body, "Acceptance criteria"))
        requirements = tuple(item for item in (outcome, *scope) if item)
        if not requirements:
            requirements = (title or f"Implement {repository}#{issue_number}",)
        if not criteria:
            criteria = ("Work acceptance criteria are satisfied.",)
        surfaces = _surfaces(title, body)
        obligations = ["verification", "review_closed"]
        if "mcp" in surfaces:
            obligations.append("live_candidate_verification")
        contract = self._store.materialize_contract(
            project_id=project_id,
            work_id=f"WORK-{issue_number}",
            repository=repository,
            requirements=requirements,
            acceptance_criteria=criteria,
            affected_surfaces=surfaces,
            obligations=tuple(obligations),
            source_identity=f"github-issue:{repository}#{issue_number}",
        )
        return contract.to_json_dict()


def result_mapping(result: Any) -> dict[str, Any]:
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return dict(data)
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        value = structured.get("result", structured)
        if isinstance(value, dict):
            return dict(value)
    text = "\n".join(
        value
        for block in getattr(result, "content", ())
        if isinstance((value := getattr(block, "text", None)), str)
    ).strip()
    if text:
        decoded = json.loads(text)
        if isinstance(decoded, dict):
            return decoded
    raise ValueError("WORK_ACTIVATION_ISSUE_RESULT_INVALID")


__all__ = ["IssueLoader", "WorkActivationCoordinator", "result_mapping"]
