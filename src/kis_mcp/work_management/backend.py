from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, TypeAlias, runtime_checkable

from .contracts import PUBLIC_SCHEMA_VERSION

_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
JsonScalar: TypeAlias = str | int | float | bool | None


class ProjectOwnerType(StrEnum):
    USER = "user"
    ORG = "org"


class ProjectFieldKind(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    SINGLE_SELECT = "single_select"
    ITERATION = "iteration"
    REPOSITORY = "repository"
    UNKNOWN = "unknown"


class ProjectItemKind(StrEnum):
    ISSUE = "issue"
    PULL_REQUEST = "pull_request"
    DRAFT = "draft"
    UNKNOWN = "unknown"


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _optional_text(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, label)


def _identifier(value: str, label: str) -> str:
    normalized = _required_text(value, label)
    if _ID.fullmatch(normalized) is None:
        raise ValueError(f"{label} must use lower-case kebab-case")
    return normalized


def _opaque_id(value: str, label: str) -> str:
    normalized = _required_text(value, label)
    if any(character.isspace() for character in normalized):
        raise ValueError(f"{label} must not contain whitespace")
    return normalized


def _positive_int(value: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class ProjectBinding:
    binding_id: str
    managed_project_id: str
    provider_id: str
    owner: str
    owner_type: ProjectOwnerType
    project_number: int
    repository: str | None = None
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("project binding schema_version must be 1")
        object.__setattr__(
            self, "binding_id", _identifier(self.binding_id, "binding_id")
        )
        object.__setattr__(
            self,
            "managed_project_id",
            _identifier(self.managed_project_id, "managed_project_id"),
        )
        object.__setattr__(
            self, "provider_id", _identifier(self.provider_id, "provider_id")
        )
        object.__setattr__(self, "owner", _required_text(self.owner, "owner"))
        if not isinstance(self.owner_type, ProjectOwnerType):
            raise ValueError("owner_type must be a ProjectOwnerType value")
        object.__setattr__(
            self, "project_number", _positive_int(self.project_number, "project_number")
        )
        repository = _optional_text(self.repository, "repository")
        if repository is not None and any(
            character.isspace() for character in repository
        ):
            raise ValueError("repository must not contain whitespace")
        object.__setattr__(self, "repository", repository)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "binding_id": self.binding_id,
            "managed_project_id": self.managed_project_id,
            "provider_id": self.provider_id,
            "owner": self.owner,
            "owner_type": self.owner_type.value,
            "project_number": self.project_number,
            "repository": self.repository,
        }


@dataclass(frozen=True, slots=True)
class ProjectFieldOption:
    option_id: str
    name: str
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("project field option schema_version must be 1")
        object.__setattr__(self, "option_id", _opaque_id(self.option_id, "option_id"))
        object.__setattr__(self, "name", _required_text(self.name, "option name"))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "option_id": self.option_id,
            "name": self.name,
        }


@dataclass(frozen=True, slots=True)
class ProjectField:
    field_id: str
    name: str
    kind: ProjectFieldKind
    options: tuple[ProjectFieldOption, ...] = ()
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("project field schema_version must be 1")
        object.__setattr__(self, "field_id", _opaque_id(self.field_id, "field_id"))
        object.__setattr__(self, "name", _required_text(self.name, "field name"))
        if not isinstance(self.kind, ProjectFieldKind):
            raise ValueError("kind must be a ProjectFieldKind value")
        if any(not isinstance(option, ProjectFieldOption) for option in self.options):
            raise ValueError("options must contain ProjectFieldOption values")
        if self.kind is not ProjectFieldKind.SINGLE_SELECT and self.options:
            raise ValueError("options are allowed only for single_select fields")
        option_ids = [option.option_id for option in self.options]
        option_names = [option.name.casefold() for option in self.options]
        if len(set(option_ids)) != len(option_ids) or len(set(option_names)) != len(
            option_names
        ):
            raise ValueError("field options must have unique IDs and names")
        object.__setattr__(
            self,
            "options",
            tuple(
                sorted(
                    self.options,
                    key=lambda option: (option.name.casefold(), option.option_id),
                )
            ),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "field_id": self.field_id,
            "name": self.name,
            "kind": self.kind.value,
            "options": [option.to_json_dict() for option in self.options],
        }


@dataclass(frozen=True, slots=True)
class ProjectFieldValue:
    field_name: str
    value: JsonScalar
    field_id: str | None = None
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("project field value schema_version must be 1")
        object.__setattr__(
            self, "field_name", _required_text(self.field_name, "field_name")
        )
        object.__setattr__(self, "field_id", _optional_text(self.field_id, "field_id"))
        if self.value is not None and not isinstance(
            self.value, (str, int, float, bool)
        ):
            raise ValueError("field value must be a JSON scalar")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "field_name": self.field_name,
            "field_id": self.field_id,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class ProjectItem:
    item_id: str
    kind: ProjectItemKind
    title: str
    repository: str | None = None
    number: int | None = None
    state: str | None = None
    url: str | None = None
    revision: str | None = None
    field_values: tuple[ProjectFieldValue, ...] = ()
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("project item schema_version must be 1")
        object.__setattr__(self, "item_id", _opaque_id(self.item_id, "item_id"))
        if not isinstance(self.kind, ProjectItemKind):
            raise ValueError("kind must be a ProjectItemKind value")
        object.__setattr__(self, "title", _required_text(self.title, "item title"))
        repository = _optional_text(self.repository, "repository")
        if repository is not None and any(
            character.isspace() for character in repository
        ):
            raise ValueError("repository must not contain whitespace")
        object.__setattr__(self, "repository", repository)
        if self.number is not None:
            object.__setattr__(self, "number", _positive_int(self.number, "number"))
        object.__setattr__(self, "state", _optional_text(self.state, "state"))
        object.__setattr__(self, "url", _optional_text(self.url, "url"))
        object.__setattr__(self, "revision", _optional_text(self.revision, "revision"))
        if any(not isinstance(value, ProjectFieldValue) for value in self.field_values):
            raise ValueError("field_values must contain ProjectFieldValue values")
        names = [value.field_name.casefold() for value in self.field_values]
        if len(set(names)) != len(names):
            raise ValueError("field_values must have unique field names")
        object.__setattr__(
            self,
            "field_values",
            tuple(
                sorted(self.field_values, key=lambda value: value.field_name.casefold())
            ),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "item_id": self.item_id,
            "kind": self.kind.value,
            "title": self.title,
            "repository": self.repository,
            "number": self.number,
            "state": self.state,
            "url": self.url,
            "revision": self.revision,
            "field_values": [value.to_json_dict() for value in self.field_values],
        }


@dataclass(frozen=True, slots=True)
class ProjectInventoryPage:
    items: tuple[ProjectItem, ...]
    next_cursor: str | None = None
    has_next_page: bool = False
    truncated: bool = False
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("project inventory page schema_version must be 1")
        if any(not isinstance(item, ProjectItem) for item in self.items):
            raise ValueError("items must contain ProjectItem values")
        item_ids = [item.item_id for item in self.items]
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("page item IDs must be unique")
        if not isinstance(self.has_next_page, bool) or not isinstance(
            self.truncated, bool
        ):
            raise ValueError("page flags must be booleans")
        object.__setattr__(
            self, "next_cursor", _optional_text(self.next_cursor, "next_cursor")
        )
        if self.has_next_page and self.next_cursor is None:
            raise ValueError("next_cursor is required when has_next_page is true")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "items": [item.to_json_dict() for item in self.items],
            "next_cursor": self.next_cursor,
            "has_next_page": self.has_next_page,
            "truncated": self.truncated,
        }


@dataclass(frozen=True, slots=True)
class ProjectInventory:
    binding: ProjectBinding
    title: str
    project_node_id: str | None = None
    closed: bool = False
    fields: tuple[ProjectField, ...] = ()
    items: tuple[ProjectItem, ...] = ()
    truncated: bool = False
    next_cursor: str | None = None
    schema_version: int = PUBLIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PUBLIC_SCHEMA_VERSION:
            raise ValueError("project inventory schema_version must be 1")
        if not isinstance(self.binding, ProjectBinding):
            raise ValueError("binding must be a ProjectBinding")
        object.__setattr__(self, "title", _required_text(self.title, "project title"))
        object.__setattr__(
            self,
            "project_node_id",
            _optional_text(self.project_node_id, "project_node_id"),
        )
        if not isinstance(self.closed, bool) or not isinstance(self.truncated, bool):
            raise ValueError("inventory flags must be booleans")
        if any(not isinstance(field, ProjectField) for field in self.fields):
            raise ValueError("fields must contain ProjectField values")
        if any(not isinstance(item, ProjectItem) for item in self.items):
            raise ValueError("items must contain ProjectItem values")
        field_ids = [field.field_id for field in self.fields]
        field_names = [field.name.casefold() for field in self.fields]
        if len(set(field_ids)) != len(field_ids):
            raise ValueError("inventory field IDs must be unique")
        if len(set(field_names)) != len(field_names):
            raise ValueError("inventory field names must be unique")
        item_ids = [item.item_id for item in self.items]
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("inventory item IDs must be unique")
        object.__setattr__(
            self,
            "fields",
            tuple(
                sorted(
                    self.fields,
                    key=lambda field: (field.name.casefold(), field.field_id),
                )
            ),
        )
        object.__setattr__(self, "items", tuple(self.items))
        object.__setattr__(
            self, "next_cursor", _optional_text(self.next_cursor, "next_cursor")
        )
        if self.truncated and self.next_cursor is None:
            raise ValueError("next_cursor is required when inventory is truncated")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "binding": self.binding.to_json_dict(),
            "title": self.title,
            "project_node_id": self.project_node_id,
            "closed": self.closed,
            "fields": [field.to_json_dict() for field in self.fields],
            "items": [item.to_json_dict() for item in self.items],
            "truncated": self.truncated,
            "next_cursor": self.next_cursor,
        }


@runtime_checkable
class ProjectInventoryBackend(Protocol):
    async def read_inventory(
        self,
        project_binding: ProjectBinding,
        *,
        field_names: tuple[str, ...] = (),
        item_limit: int = 100,
        query: str | None = None,
    ) -> ProjectInventory: ...


__all__ = [
    "JsonScalar",
    "ProjectBinding",
    "ProjectField",
    "ProjectFieldKind",
    "ProjectFieldOption",
    "ProjectFieldValue",
    "ProjectInventory",
    "ProjectInventoryBackend",
    "ProjectInventoryPage",
    "ProjectItem",
    "ProjectItemKind",
    "ProjectOwnerType",
]
