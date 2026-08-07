from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol

from ....work_management import (
    ProjectBinding,
    ProjectField,
    ProjectFieldKind,
    ProjectFieldOption,
    ProjectFieldValue,
    ProjectInventory,
    ProjectInventoryBackend,
    ProjectItem,
    ProjectItemKind,
)

_PROJECT_GET = "projects_get"
_PROJECT_LIST = "projects_list"


class ToolCaller(Protocol):
    async def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Any: ...


class GitHubProjectInventoryError(RuntimeError):
    pass


def _invalid(operation: str, reason: str) -> GitHubProjectInventoryError:
    return GitHubProjectInventoryError(
        f"GITHUB_PROJECT_INVENTORY_INVALID_RESPONSE: {operation}: {reason}"
    )


def _result_mapping(result: Any, operation: str) -> dict[str, Any]:
    if isinstance(result, Mapping):
        document = dict(result)
    else:
        data = getattr(result, "data", None)
        structured = getattr(result, "structured_content", None)
        if isinstance(data, Mapping):
            document = dict(data)
        elif isinstance(structured, Mapping):
            document = dict(structured)
        else:
            texts = [
                text
                for block in getattr(result, "content", ())
                if isinstance((text := getattr(block, "text", None)), str)
            ]
            if not texts:
                raise _invalid(operation, "result was not a mapping")
            try:
                parsed = json.loads("\n".join(texts))
            except json.JSONDecodeError as exc:
                raise _invalid(operation, "result text was not JSON") from exc
            if not isinstance(parsed, Mapping):
                raise _invalid(operation, "result JSON was not an object")
            document = dict(parsed)

    for key in ("result", "data"):
        nested = document.get(key)
        if isinstance(nested, Mapping):
            document = dict(nested)
    return document


def _required_text(value: Any, operation: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _invalid(operation, f"{label} was missing")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip() or None


def _provider_text(value: Any, operation: str, label: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, Mapping):
        for key in ("raw", "html"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    raise _invalid(operation, f"{label} was missing")


def _provider_id(raw: Mapping[str, Any], operation: str, label: str) -> str:
    for key in ("node_id", "nodeId"):
        candidate = raw.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    candidate = raw.get("id")
    if isinstance(candidate, bool) or not isinstance(candidate, (str, int)):
        raise _invalid(operation, f"{label} was missing")
    normalized = str(candidate).strip()
    if not normalized:
        raise _invalid(operation, f"{label} was missing")
    return normalized


def _nodes(
    document: Mapping[str, Any],
    key: str,
    operation: str,
) -> tuple[list[Mapping[str, Any]], Mapping[str, Any]]:
    container: Any = document.get(key)
    if container is None and key[:-1] in document:
        container = document[key[:-1]]
    page_source: Mapping[str, Any] = document
    if isinstance(container, Mapping):
        page_source = container
        container = container.get("nodes", container.get("items"))
    if container is None and isinstance(document.get("nodes"), list):
        container = document["nodes"]
    if not isinstance(container, list):
        raise _invalid(operation, f"{key} collection was missing")
    if any(not isinstance(item, Mapping) for item in container):
        raise _invalid(operation, f"{key} collection contained a non-object")
    return [dict(item) for item in container], page_source


def _page_info(document: Mapping[str, Any], operation: str) -> tuple[bool, str | None]:
    raw = document.get("pageInfo", document.get("page_info", {}))
    if raw is None:
        raw = {}
    if not isinstance(raw, Mapping):
        raise _invalid(operation, "pageInfo was not an object")
    has_next = raw.get("hasNextPage", raw.get("has_next_page", False))
    if not isinstance(has_next, bool):
        raise _invalid(operation, "hasNextPage was not boolean")
    cursor = _optional_text(
        raw.get("nextCursor", raw.get("endCursor", raw.get("next_cursor")))
    )
    if has_next and cursor is None:
        raise _invalid(operation, "next cursor was missing")
    return has_next, cursor


def _field_kind(value: Any) -> ProjectFieldKind:
    normalized = str(value or "").strip().replace("-", "_").casefold()
    return {
        "text": ProjectFieldKind.TEXT,
        "number": ProjectFieldKind.NUMBER,
        "date": ProjectFieldKind.DATE,
        "single_select": ProjectFieldKind.SINGLE_SELECT,
        "singleselect": ProjectFieldKind.SINGLE_SELECT,
        "iteration": ProjectFieldKind.ITERATION,
    }.get(normalized, ProjectFieldKind.UNKNOWN)


def _item_kind(value: Any) -> ProjectItemKind:
    normalized = str(value or "").strip().replace("-", "_").casefold()
    return {
        "issue": ProjectItemKind.ISSUE,
        "pull_request": ProjectItemKind.PULL_REQUEST,
        "pullrequest": ProjectItemKind.PULL_REQUEST,
        "draft": ProjectItemKind.DRAFT,
        "draft_issue": ProjectItemKind.DRAFT,
        "redacted": ProjectItemKind.UNKNOWN,
    }.get(normalized, ProjectItemKind.UNKNOWN)


def _field_options(raw: Any, operation: str) -> tuple[ProjectFieldOption, ...]:
    if raw is None:
        return ()
    if isinstance(raw, Mapping):
        raw = raw.get("nodes", raw.get("options"))
    if not isinstance(raw, list):
        raise _invalid(operation, "field options were not an array")
    options: list[ProjectFieldOption] = []
    for value in raw:
        if not isinstance(value, Mapping):
            raise _invalid(operation, "field option was not an object")
        options.append(
            ProjectFieldOption(
                option_id=_provider_id(value, operation, "option id"),
                name=_provider_text(value.get("name"), operation, "option name"),
            )
        )
    return tuple(options)


def _normalize_field(raw: Mapping[str, Any], operation: str) -> ProjectField:
    kind = _field_kind(raw.get("dataType", raw.get("data_type", raw.get("type"))))
    options = _field_options(raw.get("options"), operation)
    if kind is not ProjectFieldKind.SINGLE_SELECT:
        options = ()
    return ProjectField(
        field_id=_provider_id(raw, operation, "field id"),
        name=_required_text(raw.get("name"), operation, "field name"),
        kind=kind,
        options=options,
    )


def _repository_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if not isinstance(value, Mapping):
        return None
    direct = value.get("nameWithOwner", value.get("name_with_owner", value.get("full_name")))
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    owner = value.get("owner")
    name = value.get("name")
    if isinstance(owner, Mapping):
        owner = owner.get("login", owner.get("name"))
    if isinstance(owner, str) and owner.strip() and isinstance(name, str) and name.strip():
        return f"{owner.strip()}/{name.strip()}"
    return None


def _scalar_from_mapping(value: Mapping[str, Any]) -> Any:
    for key in (
        "value",
        "text",
        "number",
        "date",
        "name",
        "title",
        "iterationTitle",
        "iteration_title",
    ):
        candidate = value.get(key)
        if candidate is None or isinstance(candidate, (str, int, float, bool)):
            if key in value:
                return candidate
    return None


def _field_value(
    field_name: str,
    raw: Any,
    *,
    field_id: str | None = None,
) -> ProjectFieldValue:
    value = _scalar_from_mapping(raw) if isinstance(raw, Mapping) else raw
    if value is not None and not isinstance(value, (str, int, float, bool)):
        value = str(value)
    return ProjectFieldValue(field_name=field_name, field_id=field_id, value=value)


def _field_values(raw: Any, operation: str) -> tuple[ProjectFieldValue, ...]:
    if raw is None:
        return ()
    values: list[ProjectFieldValue] = []
    if isinstance(raw, Mapping):
        for name, value in raw.items():
            values.append(_field_value(str(name), value))
        return tuple(values)
    if not isinstance(raw, list):
        raise _invalid(operation, "field values were not an object or array")
    for entry in raw:
        if not isinstance(entry, Mapping):
            raise _invalid(operation, "field value was not an object")
        field = entry.get("field")
        field_name = entry.get("field_name", entry.get("fieldName"))
        field_id = entry.get("field_id", entry.get("fieldId"))
        if isinstance(field, Mapping):
            field_name = field_name or field.get("name")
            field_id = field_id or field.get("id")
        name = _required_text(field_name, operation, "field value name")
        raw_value: Any = entry.get("value")
        if "value" not in entry:
            raw_value = entry
        values.append(
            _field_value(name, raw_value, field_id=_optional_text(field_id))
        )
    return tuple(values)


def _normalize_item(raw: Mapping[str, Any], operation: str) -> ProjectItem:
    content = raw.get("content")
    content = dict(content) if isinstance(content, Mapping) else {}
    item_type = raw.get("type", raw.get("contentType"))
    if item_type is None:
        item_type = content.get("type", content.get("__typename"))
    title = raw.get("title", content.get("title"))
    repository = _repository_name(raw.get("repository")) or _repository_name(
        content.get("repository")
    )
    number = raw.get("number", content.get("number"))
    if number is not None:
        if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
            raise _invalid(operation, "item number was not a positive integer")
    state = raw.get("state", content.get("state"))
    url = raw.get("url", content.get("url"))
    values = raw.get(
        "fieldValues",
        raw.get("field_values", content.get("fieldValues", content.get("field_values"))),
    )
    return ProjectItem(
        item_id=_required_text(raw.get("id"), operation, "item id"),
        kind=_item_kind(item_type),
        title=_required_text(title, operation, "item title"),
        repository=repository,
        number=number,
        state=_optional_text(state),
        url=_optional_text(url),
        field_values=_field_values(values, operation),
    )


class GitHubProjectInventoryAdapter(ProjectInventoryBackend):
    def __init__(
        self,
        caller: ToolCaller,
        *,
        page_size: int = 50,
        max_pages: int = 20,
    ) -> None:
        if not hasattr(caller, "call_tool"):
            raise ValueError("caller must provide call_tool")
        if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= 50:
            raise ValueError("page_size must be between 1 and 50")
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or max_pages <= 0:
            raise ValueError("max_pages must be a positive integer")
        self._caller = caller
        self._page_size = page_size
        self._max_pages = max_pages

    async def _call(self, operation: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            result = await self._caller.call_tool(tool, arguments)
        except Exception as exc:
            raise GitHubProjectInventoryError(
                f"GITHUB_PROJECT_INVENTORY_FAILED: {operation}: {type(exc).__name__}"
            ) from exc
        return _result_mapping(result, operation)

    @staticmethod
    def _base_arguments(binding: ProjectBinding) -> dict[str, Any]:
        return {
            "owner": binding.owner,
            "owner_type": binding.owner_type.value,
            "project_number": binding.project_number,
        }

    async def _read_project(self, binding: ProjectBinding) -> tuple[str, str | None, bool]:
        arguments = {"method": "get_project", **self._base_arguments(binding)}
        document = await self._call("get_project", _PROJECT_GET, arguments)
        candidate = document.get("project", document.get("projectV2", document))
        if not isinstance(candidate, Mapping):
            raise _invalid("get_project", "project was not an object")
        title = _required_text(candidate.get("title"), "get_project", "project title")
        node_id = _provider_id(candidate, "get_project", "project id")
        closed = candidate.get("closed", False)
        if not isinstance(closed, bool):
            state = str(candidate.get("state", "")).casefold()
            closed = state == "closed"
        return title, node_id, closed

    async def _read_fields(self, binding: ProjectBinding) -> tuple[ProjectField, ...]:
        fields: list[ProjectField] = []
        cursor: str | None = None
        for _page in range(self._max_pages):
            arguments = {
                "method": "list_project_fields",
                **self._base_arguments(binding),
                "per_page": self._page_size,
            }
            if cursor is not None:
                arguments["after"] = cursor
            document = await self._call("list_project_fields", _PROJECT_LIST, arguments)
            nodes, page_source = _nodes(document, "fields", "list_project_fields")
            fields.extend(_normalize_field(node, "list_project_fields") for node in nodes)
            has_next, cursor = _page_info(page_source, "list_project_fields")
            if not has_next:
                return tuple(fields)
        raise _invalid("list_project_fields", "page limit exceeded")

    async def _read_items(
        self,
        binding: ProjectBinding,
        *,
        field_names: tuple[str, ...],
        item_limit: int,
    ) -> tuple[tuple[ProjectItem, ...], bool, str | None]:
        items: list[ProjectItem] = []
        cursor: str | None = None
        for _page in range(self._max_pages):
            remaining = item_limit - len(items)
            if remaining <= 0:
                return tuple(items), cursor is not None, cursor
            arguments = {
                "method": "list_project_items",
                **self._base_arguments(binding),
                "per_page": min(self._page_size, remaining),
            }
            if cursor is not None:
                arguments["after"] = cursor
            if field_names:
                arguments["field_names"] = list(field_names)
            document = await self._call("list_project_items", _PROJECT_LIST, arguments)
            nodes, page_source = _nodes(document, "items", "list_project_items")
            has_next, next_cursor = _page_info(page_source, "list_project_items")
            normalized = [
                _normalize_item(node, "list_project_items") for node in nodes
            ]
            if len(normalized) > remaining:
                if not has_next or next_cursor is None:
                    raise _invalid(
                        "list_project_items",
                        "page exceeded requested limit without a continuation cursor",
                    )
                normalized = normalized[:remaining]
            items.extend(normalized)
            if len(items) >= item_limit:
                return tuple(items), has_next, next_cursor if has_next else None
            if not has_next:
                return tuple(items), False, None
            cursor = next_cursor
        if cursor is None:
            raise _invalid("list_project_items", "page limit exceeded without cursor")
        return tuple(items), True, cursor

    async def read_inventory(
        self,
        project_binding: ProjectBinding,
        *,
        field_names: tuple[str, ...] = (),
        item_limit: int = 100,
    ) -> ProjectInventory:
        if not isinstance(project_binding, ProjectBinding):
            raise ValueError("project_binding must be a ProjectBinding")
        if project_binding.provider_id != "github-mcp":
            raise ValueError("GitHub inventory requires provider_id github-mcp")
        if isinstance(item_limit, bool) or not isinstance(item_limit, int) or item_limit <= 0:
            raise ValueError("item_limit must be a positive integer")
        normalized_fields: list[str] = []
        seen: set[str] = set()
        for field_name in field_names:
            name = _required_text(field_name, "field_names", "field name")
            key = name.casefold()
            if key in seen:
                raise ValueError("field_names must be unique")
            seen.add(key)
            normalized_fields.append(name)

        title, node_id, closed = await self._read_project(project_binding)
        fields = await self._read_fields(project_binding)
        items, truncated, next_cursor = await self._read_items(
            project_binding,
            field_names=tuple(normalized_fields),
            item_limit=item_limit,
        )
        return ProjectInventory(
            binding=project_binding,
            title=title,
            project_node_id=node_id,
            closed=closed,
            fields=fields,
            items=items,
            truncated=truncated,
            next_cursor=next_cursor,
        )


__all__ = [
    "GitHubProjectInventoryAdapter",
    "GitHubProjectInventoryError",
    "ToolCaller",
]
