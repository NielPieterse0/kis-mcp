from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable, Mapping

from .contract_intelligence_contracts import (
    ContractBudget,
    ContractDocument,
    ContractOmissions,
    ContractOperation,
    ContractRelationship,
    ContractSchema,
    ContractUnknown,
    InspectContractsRequest,
    InspectContractsResponse,
)
from .contracts import Confidence
from .errors import DiscoverError
from .read_authority import ReadAuthority
from .scanner import RepositoryScanner, ScannedFile
from .settings import DiscoverSettings

_HTTP_METHODS = ("delete", "get", "head", "options", "patch", "post", "put", "trace")


class ContractIntelligenceService:
    def __init__(self, *, boundary: Path, settings: DiscoverSettings) -> None:
        self._boundary = boundary
        self._settings = settings

    def inspect(self, request: InspectContractsRequest) -> InspectContractsResponse:
        self._validate_budget(request.budget)
        authority = ReadAuthority(self._boundary, self._settings)
        snapshot = RepositoryScanner(authority, self._settings).snapshot(request.project)
        candidates = tuple(item for item in snapshot.files if _is_contract_candidate(item))

        documents: list[ContractDocument] = []
        operations: list[ContractOperation] = []
        schemas: list[ContractSchema] = []
        relationships: list[ContractRelationship] = []
        unknowns: list[ContractUnknown] = []

        for candidate in candidates:
            lowered = candidate.label.casefold()
            if lowered.endswith((".yaml", ".yml")):
                unknowns.append(
                    ContractUnknown(
                        code="YAML_CONTRACT_PARSING_UNAVAILABLE",
                        reason="YAML contract parsing is not available in this dependency-free slice.",
                        path=candidate.label,
                    )
                )
                continue
            try:
                content = authority.read_relative_text(
                    request.project,
                    candidate.label,
                    max_bytes=self._settings.limits.max_file_bytes,
                ).content
                payload = json.loads(content)
            except DiscoverError as exc:
                unknowns.append(
                    ContractUnknown(
                        code="CONTRACT_DOCUMENT_UNREADABLE",
                        reason=exc.message,
                        path=candidate.label,
                    )
                )
                continue
            except json.JSONDecodeError:
                unknowns.append(
                    ContractUnknown(
                        code="CONTRACT_JSON_INVALID",
                        reason="The candidate contract document is not valid JSON.",
                        path=candidate.label,
                    )
                )
                continue
            if not isinstance(payload, dict):
                unknowns.append(
                    ContractUnknown(
                        code="CONTRACT_ROOT_UNSUPPORTED",
                        reason="The candidate contract root must be a JSON object.",
                        path=candidate.label,
                    )
                )
                continue

            parsed = _parse_document(candidate.label, payload)
            if parsed is None:
                unknowns.append(
                    ContractUnknown(
                        code="CONTRACT_KIND_UNRECOGNIZED",
                        reason="The JSON document does not match supported OpenAPI, JSON Schema, or MCP contract evidence.",
                        path=candidate.label,
                    )
                )
                continue
            document, found_operations, found_schemas, found_relationships = parsed
            documents.append(document)
            operations.extend(found_operations)
            schemas.extend(found_schemas)
            relationships.extend(found_relationships)

        documents = _unique_sorted(documents, key=lambda item: item.path)
        operations = _unique_sorted(operations, key=lambda item: item.operation_id)
        schemas = _unique_sorted(schemas, key=lambda item: item.schema_id)
        relationships = _unique_sorted(
            relationships,
            key=lambda item: f"{item.kind}:{item.source}:{item.target}:{item.document}",
        )
        unknowns.sort(key=lambda item: (item.code, item.path or "", item.reason))

        all_documents = tuple(documents)
        all_operations = tuple(operations)
        all_schemas = tuple(schemas)
        all_relationships = tuple(relationships)
        documents_out = all_documents[: request.budget.max_documents]
        retained_paths = {item.path for item in documents_out}
        operations_for_documents = tuple(
            item for item in all_operations if item.document in retained_paths
        )
        schemas_for_documents = tuple(item for item in all_schemas if item.document in retained_paths)
        relationships_for_documents = tuple(
            item for item in all_relationships if item.document in retained_paths
        )
        operations_out = operations_for_documents[: request.budget.max_operations]
        schemas_out = schemas_for_documents[: request.budget.max_schemas]
        relationships_out = relationships_for_documents[: request.budget.max_relationships]

        omissions = ContractOmissions(
            documents=max(0, len(all_documents) - len(documents_out)),
            operations=max(0, len(all_operations) - len(operations_out)),
            schemas=max(0, len(all_schemas) - len(schemas_out)),
            relationships=max(0, len(all_relationships) - len(relationships_out)),
        )
        reasons = set(snapshot.truncation_reasons)
        if omissions.documents:
            reasons.add("max_documents")
        if len(operations_for_documents) > request.budget.max_operations:
            reasons.add("max_operations")
        if len(schemas_for_documents) > request.budget.max_schemas:
            reasons.add("max_schemas")
        if len(relationships_for_documents) > request.budget.max_relationships:
            reasons.add("max_relationships")
        if not documents_out:
            unknowns.append(
                ContractUnknown(
                    code="NO_SUPPORTED_CONTRACT_DOCUMENTS",
                    reason="No supported local contract documents were retained.",
                )
            )
            unknowns.sort(key=lambda item: (item.code, item.path or "", item.reason))

        confidence = (
            Confidence.LOW
            if not documents_out
            else Confidence.MEDIUM
            if reasons or unknowns
            else Confidence.HIGH
        )
        response = InspectContractsResponse(
            project=snapshot.project,
            documents=documents_out,
            operations=operations_out,
            schemas=schemas_out,
            relationships=relationships_out,
            unknowns=tuple(unknowns),
            omissions=omissions,
            confidence=confidence,
            truncated=bool(reasons),
            truncation_reasons=tuple(sorted(reasons)),
            fingerprint="0" * 64,
        )
        serialized = response.to_json_dict()
        serialized.pop("fingerprint")
        return replace(response, fingerprint=_fingerprint(serialized))

    def _validate_budget(self, budget: ContractBudget) -> None:
        maxima = {
            "max_documents": self._settings.limits.max_files,
            "max_operations": self._settings.limits.max_evidence,
            "max_schemas": self._settings.limits.max_evidence,
            "max_relationships": self._settings.limits.python_max_records,
        }
        for name, maximum in maxima.items():
            if getattr(budget, name) > maximum:
                raise DiscoverError(
                    code="DISCOVER_CONTRACT_BUDGET_INVALID",
                    message="The requested contract budget exceeds configured Discover limits.",
                    reason=f"{name} must not exceed {maximum}.",
                    field=f"budget.{name}",
                    accepted=f"A positive integer not greater than {maximum}.",
                    corrective_actions=(f"Lower budget.{name}.",),
                )


def _is_contract_candidate(item: ScannedFile) -> bool:
    path = item.label.casefold().replace("\\", "/")
    name = path.rsplit("/", 1)[-1]
    if name.startswith(("openapi.", "swagger.", "asyncapi.")):
        return name.endswith((".json", ".yaml", ".yml"))
    if name.endswith(".schema.json"):
        return True
    if "/contracts/" in f"/{path}" and name.endswith((".json", ".yaml", ".yml")):
        return True
    return False


def _parse_document(path: str, payload: dict[str, Any]):
    if isinstance(payload.get("openapi"), str) or isinstance(payload.get("swagger"), str):
        return _parse_openapi(path, payload)
    if _looks_like_json_schema(payload):
        kind = "mcp_contract" if _looks_like_mcp(path, payload) else "json_schema"
        return _parse_json_schema(path, payload, kind=kind)
    return None


def _parse_openapi(path: str, payload: dict[str, Any]):
    version = _optional_text(payload.get("openapi") or payload.get("swagger"))
    info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
    title = _optional_text(info.get("title"))
    document = ContractDocument(path=path, kind="openapi", version=version, title=title)
    operations: list[ContractOperation] = []
    schemas: list[ContractSchema] = []
    relationships: list[ContractRelationship] = []

    paths = payload.get("paths") if isinstance(payload.get("paths"), dict) else {}
    for route in sorted(paths, key=str.casefold):
        path_item = paths[route]
        if not isinstance(path_item, dict):
            continue
        for method in _HTTP_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            operation_id = _optional_text(operation.get("operationId")) or f"{method.upper()} {route}"
            request_refs = tuple(sorted(_refs(operation.get("requestBody")), key=str.casefold))
            response_refs = tuple(
                sorted(_refs(operation.get("responses")), key=str.casefold)
            )
            operations.append(
                ContractOperation(
                    operation_id=operation_id,
                    document=path,
                    method=method.upper(),
                    path=route,
                    summary=_optional_text(operation.get("summary")),
                    request_refs=request_refs,
                    response_refs=response_refs,
                )
            )
            for target in request_refs:
                relationships.append(
                    ContractRelationship(
                        kind="request_schema",
                        source=operation_id,
                        target=target,
                        document=path,
                        provenance="openapi_json",
                    )
                )
            for target in response_refs:
                relationships.append(
                    ContractRelationship(
                        kind="response_schema",
                        source=operation_id,
                        target=target,
                        document=path,
                        provenance="openapi_json",
                    )
                )

    components = payload.get("components") if isinstance(payload.get("components"), dict) else {}
    component_schemas = components.get("schemas") if isinstance(components.get("schemas"), dict) else {}
    for name in sorted(component_schemas, key=str.casefold):
        schema = component_schemas[name]
        if not isinstance(schema, dict):
            continue
        schema_id = f"{path}#/components/schemas/{name}"
        schemas.append(_schema_record(path, name, schema_id, schema, "openapi_json"))
        relationships.extend(_schema_refs(path, schema_id, schema, "openapi_json"))
    return document, tuple(operations), tuple(schemas), tuple(relationships)


def _parse_json_schema(path: str, payload: dict[str, Any], *, kind: str):
    version = _optional_text(payload.get("$schema"))
    title = _optional_text(payload.get("title"))
    document = ContractDocument(path=path, kind=kind, version=version, title=title)
    provenance = "mcp_schema_json" if kind == "mcp_contract" else "json_schema"
    root_name = title or Path(path).name
    root_id = _optional_text(payload.get("$id")) or f"{path}#"
    schemas = [_schema_record(path, root_name, root_id, payload, provenance)]
    relationships = list(_schema_refs(path, root_id, payload, provenance))
    definitions = payload.get("$defs") if isinstance(payload.get("$defs"), dict) else payload.get("definitions")
    if isinstance(definitions, dict):
        marker = "$defs" if "$defs" in payload else "definitions"
        for name in sorted(definitions, key=str.casefold):
            schema = definitions[name]
            if not isinstance(schema, dict):
                continue
            schema_id = f"{path}#/{marker}/{name}"
            schemas.append(_schema_record(path, name, schema_id, schema, provenance))
            relationships.extend(_schema_refs(path, schema_id, schema, provenance))
    return document, (), tuple(schemas), tuple(relationships)


def _schema_record(
    document: str,
    name: str,
    schema_id: str,
    payload: Mapping[str, Any],
    provenance: str,
) -> ContractSchema:
    required = payload.get("required") if isinstance(payload.get("required"), list) else []
    properties = payload.get("properties") if isinstance(payload.get("properties"), dict) else {}
    return ContractSchema(
        schema_id=schema_id,
        document=document,
        name=name,
        schema_type=_optional_text(payload.get("type")),
        required=tuple(sorted((item for item in required if isinstance(item, str)), key=str.casefold)),
        property_count=len(properties),
        provenance=provenance,
    )


def _schema_refs(
    document: str,
    source: str,
    payload: Any,
    provenance: str,
) -> tuple[ContractRelationship, ...]:
    return tuple(
        ContractRelationship(
            kind="ref",
            source=source,
            target=target,
            document=document,
            provenance=provenance,
        )
        for target in sorted(_refs(payload), key=str.casefold)
    )


def _refs(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.strip():
            found.add(ref)
        for item in value.values():
            found.update(_refs(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_refs(item))
    return found


def _looks_like_json_schema(payload: Mapping[str, Any]) -> bool:
    return any(key in payload for key in ("$schema", "$id", "$defs", "definitions", "properties"))


def _looks_like_mcp(path: str, payload: Mapping[str, Any]) -> bool:
    combined = " ".join(
        [
            path,
            str(payload.get("title", "")),
            str(payload.get("$id", "")),
            str(payload.get("description", "")),
        ]
    ).casefold()
    return "mcp" in combined or "tool" in combined and "/contracts/" in f"/{path.casefold()}"


def _optional_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _unique_sorted(items: Iterable[Any], *, key):
    unique: dict[str, Any] = {}
    for item in items:
        unique.setdefault(key(item), item)
    return sorted(unique.values(), key=lambda item: (key(item).casefold(), key(item)))


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = ["ContractIntelligenceService"]
