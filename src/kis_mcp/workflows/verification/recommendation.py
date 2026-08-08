from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

_TOKEN = re.compile(r"[a-z0-9]+")


class MatchableWorkflow(Protocol):
    workflow_id: str
    title: str
    description: str
    capabilities: tuple[str, ...]
    activation_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkflowMatch:
    score: int
    reasons: tuple[str, ...]


def workflow_match_score(workflow: MatchableWorkflow, query: str) -> WorkflowMatch:
    query_tokens = _tokens(query)
    if not query_tokens:
        return WorkflowMatch(score=0, reasons=())

    identity = _coverage(query_tokens, _tokens(f"{workflow.workflow_id} {workflow.title}"))
    activation = max(
        (_coverage(query_tokens, _tokens(term)) for term in workflow.activation_terms),
        default=0,
    )
    description = _coverage(query_tokens, _tokens(workflow.description))
    capability = max(
        (_coverage(query_tokens, _tokens(item.replace(".", " "))) for item in workflow.capabilities),
        default=0,
    )

    score = min(
        100,
        round(0.35 * identity + 0.40 * activation + 0.10 * description + 0.15 * capability),
    )
    reasons: list[str] = []
    if identity >= 50:
        reasons.append("workflow id/title match")
    if activation >= 50:
        reasons.append("activation term match")
    if description >= 25:
        reasons.append("description match")
    if capability >= 50:
        reasons.append("capability match")
    return WorkflowMatch(score=score, reasons=tuple(reasons))


def _tokens(value: str) -> set[str]:
    return set(_TOKEN.findall(value.casefold()))


def _coverage(query_tokens: set[str], candidate_tokens: set[str]) -> int:
    if not candidate_tokens:
        return 0
    return round(100 * len(query_tokens & candidate_tokens) / len(candidate_tokens))


__all__ = ["MatchableWorkflow", "WorkflowMatch", "workflow_match_score"]
