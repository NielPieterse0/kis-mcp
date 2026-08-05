from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any

from .contracts import Confidence, ProjectIdentity


GET_CODE_CONTEXT_SCHEMA_VERSION = 1
GET_CODE_CONTEXT_TOOL = "get_code_context"
MIN_CONTEXT_CHARS = 2_000

_ALLOWED_FILE_CATEGORIES = {
    "source",
    "test",
    "contract",
    "instruction",
    "documentation",
    "configuration",
    "policy",
    "other",
}
_ALLOWED_PROVENANCE_KINDS = {
    "observed",
    "parser_confirmed",
    "git_observed",
    "conventional",
    "inferred",
}
_ALLOWED_RELATIONSHIP_KINDS = {"import", "call", "inheritance"}
_ALLOWED_CONFIDENCE = {"high", "medium", "low"}


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _positive(value: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _non_negative(value: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _terms(value: Sequence[str], label: str) -> tuple[str, ...]:
    items = tuple(value)
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ValueError(f"{label} must contain only non-empty strings")
    if len(set(items)) != len(items):
        raise ValueError(f"{label} must not contain duplicate values")
    return items


def _fingerprint(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError("context fingerprint must be 64 lowercase hexadecimal characters")
    return value


def _json_value(value: Any) -> Any:
    if hasattr(value, "to_json_dict"):
        return value.to_json_dict()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"value is not JSON-compatible: {type(value).__name__}")


class _JsonRecord:
    def to_json_dict(self) -> dict[str, Any]:
        return {field.name: _json_value(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class CodeContextBudget(_JsonRecord):
    max_chars: int
    max_files: int
    max_symbols: int
    max_relationships: int

    def __post_init__(self) -> None:
        for name in ("max_chars", "max_files", "max_symbols", "max_relationships"):
            _positive(getattr(self, name), f"context budget {name}")
        if self.max_chars < MIN_CONTEXT_CHARS:
            raise ValueError(
                f"context budget max_chars must meet the minimum of {MIN_CONTEXT_CHARS}"
            )


@dataclass(frozen=True, slots=True)
class GetCodeContextRequest(_JsonRecord):
    project: str
    task: str
    budget: CodeContextBudget

    def __post_init__(self) -> None:
        _required_text(self.project, "context project")
        _required_text(self.task, "context task")
        if not isinstance(self.budget, CodeContextBudget):
            raise ValueError("context budget must be a CodeContextBudget")


@dataclass(frozen=True, slots=True)
class ContextProvenance(_JsonRecord):
    kind: str
    provider: str
    identifier: str

    def __post_init__(self) -> None:
        if self.kind not in _ALLOWED_PROVENANCE_KINDS:
            raise ValueError("context provenance kind is unsupported")
        _required_text(self.provider, "context provenance provider")
        _required_text(self.identifier, "context provenance identifier")


@dataclass(frozen=True, slots=True)
class ContextFile(_JsonRecord):
    path: str
    category: str
    relevance_score: int
    matched_terms: tuple[str, ...]
    excerpt: str
    start_line: int
    end_line: int
    truncated: bool
    provenance: ContextProvenance

    def __post_init__(self) -> None:
        _required_text(self.path, "context file path")
        if self.category not in _ALLOWED_FILE_CATEGORIES:
            raise ValueError("context file category is unsupported")
        _non_negative(self.relevance_score, "context file relevance_score")
        _terms(self.matched_terms, "context file matched_terms")
        _required_text(self.excerpt, "context file excerpt")
        _positive(self.start_line, "context file start_line")
        _positive(self.end_line, "context file end_line")
        if self.end_line < self.start_line:
            raise ValueError("context file end_line must not precede start_line")


@dataclass(frozen=True, slots=True)
class ContextModule(_JsonRecord):
    name: str
    path: str
    relevance_score: int
    matched_terms: tuple[str, ...]
    provenance: ContextProvenance

    def __post_init__(self) -> None:
        _required_text(self.name, "context module name")
        _required_text(self.path, "context module path")
        _non_negative(self.relevance_score, "context module relevance_score")
        _terms(self.matched_terms, "context module matched_terms")


@dataclass(frozen=True, slots=True)
class ContextSymbol(_JsonRecord):
    qualified_name: str
    module: str
    name: str
    kind: str
    path: str
    line: int
    end_line: int | None
    relevance_score: int
    matched_terms: tuple[str, ...]
    provenance: ContextProvenance

    def __post_init__(self) -> None:
        for value, label in (
            (self.qualified_name, "context symbol qualified_name"),
            (self.module, "context symbol module"),
            (self.name, "context symbol name"),
            (self.kind, "context symbol kind"),
            (self.path, "context symbol path"),
        ):
            _required_text(value, label)
        _positive(self.line, "context symbol line")
        if self.end_line is not None:
            _positive(self.end_line, "context symbol end_line")
            if self.end_line < self.line:
                raise ValueError("context symbol end_line must not precede line")
        _non_negative(self.relevance_score, "context symbol relevance_score")
        _terms(self.matched_terms, "context symbol matched_terms")


@dataclass(frozen=True, slots=True)
class ContextRelationship(_JsonRecord):
    kind: str
    source: str
    target: str
    path: str
    line: int
    relevance_score: int
    confidence: str
    provenance: ContextProvenance

    def __post_init__(self) -> None:
        if self.kind not in _ALLOWED_RELATIONSHIP_KINDS:
            raise ValueError("context relationship kind is unsupported")
        for value, label in (
            (self.source, "context relationship source"),
            (self.target, "context relationship target"),
            (self.path, "context relationship path"),
        ):
            _required_text(value, label)
        _positive(self.line, "context relationship line")
        _non_negative(self.relevance_score, "context relationship relevance_score")
        if self.confidence not in _ALLOWED_CONFIDENCE:
            raise ValueError("context relationship confidence is unsupported")


@dataclass(frozen=True, slots=True)
class ContextUnknown(_JsonRecord):
    code: str
    reason: str

    def __post_init__(self) -> None:
        _required_text(self.code, "context unknown code")
        _required_text(self.reason, "context unknown reason")


@dataclass(frozen=True, slots=True)
class ContextOmissions(_JsonRecord):
    files: int
    symbols: int
    relationships: int
    unreadable_files: int

    def __post_init__(self) -> None:
        for name in ("files", "symbols", "relationships", "unreadable_files"):
            _non_negative(getattr(self, name), f"context omission {name}")


@dataclass(frozen=True, slots=True)
class GetCodeContextResponse:
    project: ProjectIdentity
    task: str
    budget: CodeContextBudget
    task_terms: tuple[str, ...]
    files: tuple[ContextFile, ...]
    modules: tuple[ContextModule, ...]
    symbols: tuple[ContextSymbol, ...]
    relationships: tuple[ContextRelationship, ...]
    instructions: tuple[str, ...]
    tests: tuple[str, ...]
    contracts: tuple[str, ...]
    git: Mapping[str, Any]
    providers: Mapping[str, Any]
    unknowns: tuple[ContextUnknown, ...]
    omissions: ContextOmissions
    confidence: Confidence
    truncated: bool
    truncation_reasons: tuple[str, ...]
    fingerprint: str
    schema_version: int = GET_CODE_CONTEXT_SCHEMA_VERSION
    tool: str = GET_CODE_CONTEXT_TOOL

    def __post_init__(self) -> None:
        if self.schema_version != GET_CODE_CONTEXT_SCHEMA_VERSION:
            raise ValueError("get_code_context schema_version must be 1")
        if self.tool != GET_CODE_CONTEXT_TOOL:
            raise ValueError("get_code_context tool identity is fixed")
        if not isinstance(self.project, ProjectIdentity):
            raise ValueError("context project identity is invalid")
        _required_text(self.task, "context task")
        _terms(self.task_terms, "context task_terms")
        for label, paths in (
            ("instructions", self.instructions),
            ("tests", self.tests),
            ("contracts", self.contracts),
        ):
            _terms(paths, f"context {label}")
        if any(not reason.strip() for reason in self.truncation_reasons):
            raise ValueError("context truncation reasons must be non-empty strings")
        if not self.truncated and self.truncation_reasons:
            raise ValueError("context truncation reasons require truncated=true")
        if self.truncated and not self.truncation_reasons:
            raise ValueError("truncated context requires a truncation reason")
        _fingerprint(self.fingerprint)
        _json_value(self.git)
        _json_value(self.providers)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool": self.tool,
            "project": self.project.to_json_dict(),
            "task": self.task,
            "budget": self.budget.to_json_dict(),
            "task_terms": list(self.task_terms),
            "files": [item.to_json_dict() for item in self.files],
            "modules": [item.to_json_dict() for item in self.modules],
            "symbols": [item.to_json_dict() for item in self.symbols],
            "relationships": [item.to_json_dict() for item in self.relationships],
            "instructions": list(self.instructions),
            "tests": list(self.tests),
            "contracts": list(self.contracts),
            "git": _json_value(self.git),
            "providers": _json_value(self.providers),
            "unknowns": [item.to_json_dict() for item in self.unknowns],
            "omissions": self.omissions.to_json_dict(),
            "confidence": self.confidence.value,
            "truncated": self.truncated,
            "truncation_reasons": list(self.truncation_reasons),
            "fingerprint": self.fingerprint,
        }


__all__ = [
    "CodeContextBudget",
    "ContextFile",
    "ContextModule",
    "ContextOmissions",
    "ContextProvenance",
    "ContextRelationship",
    "ContextSymbol",
    "ContextUnknown",
    "GET_CODE_CONTEXT_SCHEMA_VERSION",
    "GET_CODE_CONTEXT_TOOL",
    "GetCodeContextRequest",
    "GetCodeContextResponse",
    "MIN_CONTEXT_CHARS",
]
