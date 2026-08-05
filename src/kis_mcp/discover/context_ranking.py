from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable


_CAMEL_ACRONYM = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")
_WORD = re.compile(r"[a-z0-9]+")
_STOP_WORDS = frozenset(
    {
        "a",
        "add",
        "an",
        "and",
        "create",
        "for",
        "from",
        "implement",
        "in",
        "of",
        "on",
        "repair",
        "fix",
        "the",
        "to",
        "update",
        "with",
    }
)
_ALIASES = {
    "checks": "check",
    "contracts": "contract",
    "files": "file",
    "instructions": "instruction",
    "modules": "module",
    "providers": "provider",
    "relationships": "relationship",
    "schemas": "schema",
    "symbols": "symbol",
    "tests": "test",
}
_CATEGORY_INTENT = {
    "test": frozenset({"test", "testing", "verify", "verification", "check"}),
    "contract": frozenset(
        {"api", "asyncapi", "contract", "graphql", "openapi", "proto", "schema"}
    ),
    "instruction": frozenset(
        {"agent", "agents", "governance", "instruction", "policy", "rule"}
    ),
    "documentation": frozenset({"doc", "documentation", "readme"}),
    "configuration": frozenset({"config", "configuration", "setting", "settings"}),
    "policy": frozenset({"governance", "policy", "rule"}),
}


@dataclass(frozen=True, slots=True)
class RelevanceScore:
    score: int
    matched_terms: tuple[str, ...]
    git_changed: bool = False
    connected: bool = False


def task_terms(task: str) -> tuple[str, ...]:
    if not isinstance(task, str) or not task.strip():
        raise ValueError("context task must be a non-empty string")
    return _tokenize(task, remove_stop_words=True)


def score_path_candidate(
    path: str,
    *,
    category: str,
    terms: Iterable[str],
    git_changed: bool = False,
) -> RelevanceScore:
    ordered_terms = tuple(terms)
    path_tokens = set(_tokenize(path, remove_stop_words=False))
    basename = path.replace("\\", "/").rsplit("/", 1)[-1]
    basename_tokens = set(_tokenize(basename, remove_stop_words=False))
    matched = tuple(term for term in ordered_terms if term in path_tokens)
    score = len(matched) * 18
    score += sum(15 for term in matched if term in basename_tokens)
    normalized_path = path.casefold().replace("\\", "/")
    score += sum(
        5
        for term in ordered_terms
        if term not in path_tokens and len(term) >= 4 and term in normalized_path
    )
    intent_terms = _CATEGORY_INTENT.get(category, frozenset())
    if intent_terms.intersection(ordered_terms):
        score += 35
    if category == "source":
        score += 5
    elif category in {"instruction", "contract", "test"}:
        score += 3
    if git_changed:
        score += 15
    return RelevanceScore(
        score=score,
        matched_terms=matched,
        git_changed=git_changed,
    )


def score_named_candidate(
    *,
    identifier: str,
    name: str,
    path: str,
    kind: str,
    terms: Iterable[str],
    parent_score: int = 0,
) -> RelevanceScore:
    ordered_terms = tuple(terms)
    identifier_tokens = set(_tokenize(identifier, remove_stop_words=False))
    name_tokens = set(_tokenize(name, remove_stop_words=False))
    path_tokens = set(_tokenize(path, remove_stop_words=False))
    matched = tuple(
        term
        for term in ordered_terms
        if term in identifier_tokens or term in name_tokens or term in path_tokens
    )
    score = max(0, parent_score // 3)
    score += sum(45 for term in matched if term in name_tokens)
    score += sum(
        20 for term in matched if term in identifier_tokens and term not in name_tokens
    )
    score += sum(
        8
        for term in matched
        if term in path_tokens
        and term not in identifier_tokens
        and term not in name_tokens
    )
    if kind in {"class", "function", "async_function", "method", "async_method"}:
        score += 3
    return RelevanceScore(score=score, matched_terms=matched)


def score_relationship_candidate(
    *,
    kind: str,
    source: str,
    target: str,
    path: str,
    terms: Iterable[str],
    selected: set[str] | frozenset[str],
) -> RelevanceScore:
    ordered_terms = tuple(terms)
    tokens = set(
        _tokenize(
            f"{kind} {source} {target} {path}",
            remove_stop_words=False,
        )
    )
    matched = tuple(term for term in ordered_terms if term in tokens)
    connected = source in selected or target in selected
    score = len(matched) * 15
    if connected:
        score += 40
    if kind in {"call", "inheritance"}:
        score += 4
    elif kind == "import":
        score += 2
    return RelevanceScore(
        score=score,
        matched_terms=matched,
        connected=connected,
    )


def relevance_sort_key(score: int, *identities: str) -> tuple[Any, ...]:
    normalized: list[str] = []
    for identity in identities:
        normalized.extend((identity.casefold(), identity))
    return (-score, *normalized)


def stable_fingerprint(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _tokenize(value: str, *, remove_stop_words: bool) -> tuple[str, ...]:
    expanded = _CAMEL_ACRONYM.sub(r"\1 \2", value)
    expanded = _CAMEL_BOUNDARY.sub(r"\1 \2", expanded)
    raw = _WORD.findall(expanded.casefold())
    ordered: list[str] = []
    seen: set[str] = set()
    for token in raw:
        normalized = _ALIASES.get(token, token)
        if remove_stop_words and normalized in _STOP_WORDS:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return tuple(ordered)


__all__ = [
    "RelevanceScore",
    "relevance_sort_key",
    "score_named_candidate",
    "score_path_candidate",
    "score_relationship_candidate",
    "stable_fingerprint",
    "task_terms",
]
