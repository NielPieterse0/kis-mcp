from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from pathlib import Path, PureWindowsPath
from typing import Any

from fastmcp.exceptions import ToolError

from ..config import load_runtime_config
from ..paths import PathValidationError, is_within_windows_boundary, resolve_windows_effective_path
from ..projects.settings import load_project_registry_settings
from .profiles import verify_provider_profile
from .provider import ImportIsolateProvider
from .settings import ExternalAcquisitionSettings, load_external_acquisition_settings

_LOGICAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_PROJECT_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_CREDENTIAL_REF = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
_SECRET_NAME = re.compile(r"(?:token|secret|password|credential|api[_-]?key|authorization|auth)", re.IGNORECASE)
_INPUT_KEYS = {"project", "profile", "recipe", "recipe_hash", "parameters", "approved"}
_RESULT_KEYS = {
    "schema_version",
    "provider",
    "provider_type",
    "project_id",
    "profile_id",
    "recipe_id",
    "recipe_hash",
    "content_class",
    "artifact_sha256",
    "byte_count",
    "artifact_relative_path",
    "provider_implementation_revision",
    "container_image_digest",
    "credential_references",
    "state",
    "failure_code",
}


def _read_recipe(project_root: str, recipe_directory: str, recipe_id: str) -> tuple[str, bytes]:
    candidate = str(
        PureWindowsPath(project_root)
        / PureWindowsPath(recipe_directory)
        / f"{recipe_id}.json"
    )
    try:
        effective_root = resolve_windows_effective_path(
            project_root,
            base=project_root,
            follow_final=True,
        )
        effective_recipe = resolve_windows_effective_path(
            candidate,
            base=project_root,
            follow_final=True,
        )
    except PathValidationError as exc:
        raise ToolError("REGISTERED_RECIPE_PATH_INVALID: recipe path could not be safely resolved") from exc
    if not is_within_windows_boundary(effective_recipe, boundary=effective_root):
        raise ToolError("REGISTERED_RECIPE_PATH_ESCAPE: recipe resolved outside the registered project")
    path = Path(effective_recipe)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ToolError(f"REGISTERED_RECIPE_UNAVAILABLE: {recipe_id}") from exc
    if len(data) > 1024 * 1024:
        raise ToolError("REGISTERED_RECIPE_TOO_LARGE: recipe exceeds 1 MiB")
    return effective_recipe, data


def _required_text(value: Any, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ToolError(f"INVALID_ACQUISITION_REQUEST: {label} is invalid")
    return value


def _normalize_parameter_scalar(item: Any, name: str, settings: ExternalAcquisitionSettings) -> object:
    if isinstance(item, str):
        if len(item) > settings.limits.max_parameter_string_chars:
            raise ToolError(f"INVALID_ACQUISITION_REQUEST: parameter {name} is too long")
        return item
    if isinstance(item, bool):
        return item
    if isinstance(item, int):
        return item
    if isinstance(item, float):
        if not math.isfinite(item):
            raise ToolError(f"INVALID_ACQUISITION_REQUEST: parameter {name} must be finite")
        return item
    raise ToolError(f"INVALID_ACQUISITION_REQUEST: parameter {name} must be a scalar")


def _normalize_parameters(
    value: Any,
    allowed: tuple[str, ...],
    settings: ExternalAcquisitionSettings,
    request_schema_version: int,
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ToolError("INVALID_ACQUISITION_REQUEST: parameters must be an object")
    if len(value) > settings.limits.max_parameters:
        raise ToolError("INVALID_ACQUISITION_REQUEST: too many parameters")
    unknown = sorted(str(key) for key in set(value) - set(allowed))
    if unknown:
        raise ToolError("UNAUTHORIZED_ACQUISITION_PARAMETERS: " + ", ".join(unknown))
    normalized: dict[str, object] = {}
    for key, item in value.items():
        name = _required_text(key, _LOGICAL_ID, "parameter name")
        if _SECRET_NAME.search(name):
            raise ToolError("SECRET_VALUE_FORBIDDEN: secret-like acquisition parameters are not allowed")
        if isinstance(item, list):
            if request_schema_version != 2 or not 1 <= len(item) <= 64:
                raise ToolError(f"INVALID_ACQUISITION_REQUEST: parameter {name} list is not permitted")
            normalized[name] = [_normalize_parameter_scalar(entry, name, settings) for entry in item]
        else:
            normalized[name] = _normalize_parameter_scalar(item, name, settings)
    return normalized


def _validate_relative_artifact_path(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 512 or ":" in value:
        raise ToolError("IMPORT_ISOLATE_RESULT_INVALID: artifact_relative_path is invalid")
    path = PureWindowsPath(value)
    if path.is_absolute() or path.drive or ".." in path.parts:
        raise ToolError("IMPORT_ISOLATE_RESULT_INVALID: artifact path must remain provider-relative")
    return value


def _validate_provider_result(result: Any, request: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(result, Mapping) or set(result) != _RESULT_KEYS:
        raise ToolError("IMPORT_ISOLATE_RESULT_INVALID: result does not match the strict contract")
    if result.get("schema_version") != 1 or result.get("provider") != "import-isolate":
        raise ToolError("IMPORT_ISOLATE_RESULT_INVALID: provider identity/schema mismatch")
    expected = {
        "project_id": request["project_id"],
        "profile_id": request["profile_id"],
        "recipe_id": request["recipe_id"],
        "recipe_hash": request["recipe_hash"],
    }
    if any(result.get(key) != value for key, value in expected.items()):
        raise ToolError("PROVIDER_RESULT_IDENTITY_MISMATCH: import-isolate returned a different request identity")
    if result.get("provider_type") not in {"http", "firecrawl-mcp"}:
        raise ToolError("IMPORT_ISOLATE_RESULT_INVALID: unsupported provider_type")
    if result.get("content_class") not in {"data-evidence", "web-evidence", "executable-source"}:
        raise ToolError("IMPORT_ISOLATE_RESULT_INVALID: unsupported content_class")
    for key in ("artifact_sha256", "provider_implementation_revision", "container_image_digest"):
        value = result.get(key)
        if not isinstance(value, str) or _HASH.fullmatch(value) is None:
            raise ToolError(f"IMPORT_ISOLATE_RESULT_INVALID: {key} is invalid")
    byte_count = result.get("byte_count")
    if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count < 0:
        raise ToolError("IMPORT_ISOLATE_RESULT_INVALID: byte_count is invalid")
    _validate_relative_artifact_path(result.get("artifact_relative_path"))
    refs = result.get("credential_references")
    if not isinstance(refs, list) or len(refs) != len(set(refs)):
        raise ToolError("IMPORT_ISOLATE_RESULT_INVALID: credential_references must be a unique array")
    for item in refs:
        if not isinstance(item, str) or _CREDENTIAL_REF.fullmatch(item) is None or "=" in item:
            raise ToolError("IMPORT_ISOLATE_RESULT_INVALID: credential references must be logical names only")
    if result.get("state") != "success" or result.get("failure_code") is not None:
        raise ToolError("IMPORT_ISOLATE_RESULT_INVALID: provider did not return a successful receipt")
    return dict(result)


class RegisteredAcquisitionService:
    def __init__(self, settings: ExternalAcquisitionSettings, projects: Any, provider: Any) -> None:
        self.settings = settings
        self.projects = projects
        self.provider = provider

    def execute(self, arguments: Mapping[str, Any]) -> dict[str, object]:
        if not isinstance(arguments, Mapping) or set(arguments) != _INPUT_KEYS:
            raise ToolError("INVALID_ACQUISITION_REQUEST: arguments do not match the fixed schema")
        project_id = _required_text(arguments.get("project"), _PROJECT_ID, "project")
        profile_id = _required_text(arguments.get("profile"), _PROJECT_ID, "profile")
        recipe_id = _required_text(arguments.get("recipe"), _LOGICAL_ID, "recipe")
        recipe_hash = arguments.get("recipe_hash")
        if not isinstance(recipe_hash, str) or _HASH.fullmatch(recipe_hash) is None:
            raise ToolError("INVALID_ACQUISITION_REQUEST: recipe_hash must be sha256:<64 lowercase hex>")
        if arguments.get("approved") is not True:
            raise ToolError("APPROVAL_REQUIRED: registered acquisition requires approved=true")
        try:
            project = self.projects.project(project_id)
        except KeyError as exc:
            raise ToolError(f"REGISTERED_PROJECT_REQUIRED: {project_id}") from exc
        try:
            authorization = self.settings.authorization(project_id, profile_id)
        except KeyError as exc:
            raise ToolError(f"UNAUTHORIZED_ACQUISITION_PROFILE: {project_id}/{profile_id}") from exc
        try:
            provider_project = self.projects.project(self.settings.provider_project_id)
        except KeyError as exc:
            raise ToolError(f"REGISTERED_PROVIDER_PROJECT_REQUIRED: {self.settings.provider_project_id}") from exc
        verify_provider_profile(
            provider_project.local_root,
            self.settings.provider_profile_policy_relative_path,
            authorization,
        )
        if not recipe_id.startswith(authorization.recipe_id_prefix):
            raise ToolError("UNAUTHORIZED_ACQUISITION_RECIPE: recipe is outside the configured namespace")
        parameters = _normalize_parameters(
            arguments.get("parameters"),
            authorization.allowed_parameter_keys,
            self.settings,
            authorization.request_schema_version,
        )
        recipe_path, recipe_bytes = _read_recipe(project.local_root, authorization.recipe_directory, recipe_id)
        actual_hash = "sha256:" + hashlib.sha256(recipe_bytes).hexdigest()
        if actual_hash != recipe_hash:
            raise ToolError("RECIPE_HASH_MISMATCH: registered recipe bytes do not match the approved hash")
        provider_request: dict[str, object] = {
            "schema_version": authorization.request_schema_version,
            "project_id": project_id,
            "profile_id": profile_id,
            "recipe_id": recipe_id,
            "recipe_hash": recipe_hash,
            "parameters": parameters,
        }
        request_chars = len(json.dumps(provider_request, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False))
        if request_chars > self.settings.limits.max_request_json_chars:
            raise ToolError("INVALID_ACQUISITION_REQUEST: normalized request exceeds configured JSON budget")
        result = self.provider.acquire(provider_request, recipe_path)
        return _validate_provider_result(result, provider_request)


def execute_registered_acquisition_operation(arguments: Mapping[str, Any]) -> dict[str, object]:
    settings = load_external_acquisition_settings()
    projects = load_project_registry_settings()
    try:
        provider_project = projects.project(settings.provider_project_id)
    except KeyError as exc:
        raise ToolError(f"REGISTERED_PROVIDER_PROJECT_REQUIRED: {settings.provider_project_id}") from exc
    runtime = load_runtime_config()
    provider = ImportIsolateProvider(
        provider_project.local_root,
        settings.provider_script_relative_path,
        runtime.temp_root,
    )
    return RegisteredAcquisitionService(settings, projects, provider).execute(arguments)


__all__ = ["RegisteredAcquisitionService", "execute_registered_acquisition_operation"]
