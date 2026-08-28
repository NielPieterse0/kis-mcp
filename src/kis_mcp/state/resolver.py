from __future__ import annotations

import hashlib
import json
import ntpath
import re
from collections.abc import Iterable

from kis_mcp.paths import (
    PathValidationError,
    is_within_windows_boundary,
    normalize_windows_path,
)

from .contract import (
    APPROVED_PROJECT_BOUNDARY,
    APPROVED_STATE_ROOT,
    FINGERPRINT_CONTRACT,
    NAMESPACE_VERSION,
    SCHEMA_VERSION,
    SPEC_BY_CLASS,
    StateNamespace,
    StateNamespaceError,
    StateNamespaceRequest,
    StateOwnershipClass,
)
from .identity import (
    normalize_identity_mapping,
    normalize_ownership,
    normalize_state_key,
)

_fingerprint_contract = FINGERPRINT_CONTRACT
_canonical = _fingerprint_contract["canonical_json"]


def _canonical_json(value: object) -> bytes:
    separators = tuple(str(item) for item in _canonical["separators"])
    text = json.dumps(
        value,
        ensure_ascii=bool(_canonical["ensure_ascii"]),
        separators=(separators[0], separators[1]),
        sort_keys=bool(_canonical["sort_keys"]),
    )
    if bool(_canonical["trailing_newline"]):
        text += "\n"
    return text.encode(str(_fingerprint_contract["encoding"]))


def _fingerprint(
    namespace_version: int,
    ownership: StateOwnershipClass,
    state_key: str | None,
    identities: dict[str, str],
    relative_path: str,
) -> str:
    available = {
        "schema_version": SCHEMA_VERSION,
        "namespace_version": namespace_version,
        "ownership_class": ownership.value,
        "state_key": state_key,
        "identities": dict(identities),
        "relative_path": relative_path,
    }
    try:
        document = {
            str(field): available[str(field)]
            for field in _fingerprint_contract["document_fields"]
        }
    except KeyError as exc:
        raise RuntimeError(
            f"STATE_CONTRACT_INVALID: unsupported fingerprint field {exc.args[0]}"
        ) from exc
    digest = hashlib.new(str(_fingerprint_contract["algorithm"]))
    digest.update(_canonical_json(document))
    return digest.hexdigest()


class StateNamespaceResolver:
    def __init__(self, *, state_root: str = APPROVED_STATE_ROOT) -> None:
        try:
            normalized = normalize_windows_path(
                state_root,
                base=APPROVED_PROJECT_BOUNDARY,
            )
        except PathValidationError as exc:
            raise StateNamespaceError(
                "STATE_ROOT_INVALID",
                "state root is not a valid Windows path",
            ) from exc
        if ntpath.normcase(normalized) != ntpath.normcase(APPROVED_STATE_ROOT):
            raise StateNamespaceError(
                "STATE_ROOT_INVALID",
                "state root must equal the approved KIS state root",
                {"approved_state_root": APPROVED_STATE_ROOT},
            )
        self.state_root = APPROVED_STATE_ROOT

    def resolve(self, request: StateNamespaceRequest) -> StateNamespace:
        if not isinstance(request, StateNamespaceRequest):
            raise StateNamespaceError(
                "STATE_REQUEST_INVALID",
                "request must be StateNamespaceRequest",
            )
        ownership = normalize_ownership(request.ownership)
        spec = SPEC_BY_CLASS[ownership]
        state_key = normalize_state_key(request.state_key, required=spec.state_key_required)
        identities = normalize_identity_mapping(
            request.identities,
            required=spec.required_identity_keys,
            label="identities",
        )
        if request.expected_identities is not None:
            expected = normalize_identity_mapping(
                request.expected_identities,
                required=spec.required_identity_keys,
                label="expected_identities",
            )
            mismatched = [
                key
                for key in spec.required_identity_keys
                if identities[key] != expected[key]
            ]
            if mismatched:
                raise StateNamespaceError(
                    "STATE_IDENTITY_STALE",
                    "request identities do not match the expected current identity",
                    {"mismatched_keys": ",".join(mismatched)},
                )

        substitutions = {**identities, "state_key": state_key or ""}
        try:
            relative_path = spec.namespace_template.format(**substitutions).replace("/", "\\")
        except (KeyError, ValueError) as exc:
            raise RuntimeError(
                "STATE_CONTRACT_INVALID: ownership namespace template cannot be resolved"
            ) from exc
        relative_path = ntpath.normpath(relative_path)
        if ntpath.isabs(relative_path) or relative_path in {"", "."}:
            raise StateNamespaceError(
                "STATE_NAMESPACE_INVALID",
                "ownership contract produced an invalid relative namespace",
            )
        path = ntpath.normpath(ntpath.join(self.state_root, relative_path))
        if not is_within_windows_boundary(path, boundary=self.state_root):
            raise StateNamespaceError(
                "STATE_NAMESPACE_ESCAPE",
                "resolved namespace escaped the approved KIS state root",
            )
        namespace_version = NAMESPACE_VERSION
        fingerprint = _fingerprint(
            namespace_version,
            ownership,
            state_key,
            identities,
            relative_path,
        )
        return StateNamespace(
            namespace_version=namespace_version,
            ownership=ownership,
            state_key=state_key,
            identities=tuple(identities.items()),
            relative_path=relative_path,
            path=path,
            identity_fingerprint=fingerprint,
        )

    def resolve_many(
        self,
        requests: Iterable[StateNamespaceRequest],
    ) -> tuple[StateNamespace, ...]:
        resolved = tuple(self.resolve(request) for request in requests)
        validate_namespace_uniqueness(resolved)
        return resolved


def _validate_namespace_pair(
    previous: StateNamespace,
    current: StateNamespace,
) -> None:
    previous_key = ntpath.normcase(previous.path)
    current_key = ntpath.normcase(current.path)
    if current_key == previous_key:
        raise StateNamespaceError(
            "STATE_NAMESPACE_COLLISION",
            "state namespaces must be unique within one resolved set",
            {"relative_path": current.relative_path},
        )
    try:
        common = ntpath.commonpath([previous_key, current_key])
    except ValueError:
        return
    if common in {previous_key, current_key}:
        raise StateNamespaceError(
            "STATE_NAMESPACE_COLLISION",
            "state namespaces must not have an ancestor or descendant overlap",
            {
                "first_relative_path": previous.relative_path,
                "second_relative_path": current.relative_path,
            },
        )



def classify_relative_namespace(relative_path: str) -> StateNamespaceRequest | None:
    """Classify one relative state namespace using canonical ownership templates."""
    candidate = ntpath.normpath(str(relative_path).replace("/", "\\"))
    if ntpath.isabs(candidate) or candidate in {"", "."} or candidate.startswith("..\\"):
        return None
    for ownership, spec in SPEC_BY_CLASS.items():
        template = spec.namespace_template.replace("/", "\\")
        fields = re.findall(r"\{([^{}]+)\}", template)
        pattern = re.escape(template)
        for field in fields:
            pattern = pattern.replace(re.escape("{" + field + "}"), rf"(?P<{field}>[^\\]+)")
        match = re.fullmatch(pattern, candidate, flags=re.IGNORECASE)
        if match is None:
            continue
        values = match.groupdict()
        state_key = values.pop("state_key", None)
        request = StateNamespaceRequest(ownership=ownership, state_key=state_key, identities=values)
        normalized_key = normalize_state_key(request.state_key, required=spec.state_key_required)
        identities = normalize_identity_mapping(request.identities, required=spec.required_identity_keys, label="identities")
        rebuilt = ntpath.normpath(spec.namespace_template.format(**identities, state_key=normalized_key or "").replace("/", "\\"))
        if ntpath.normcase(rebuilt) == ntpath.normcase(candidate):
            return StateNamespaceRequest(ownership=ownership, state_key=normalized_key, identities=identities)
    return None

def validate_namespace_uniqueness(namespaces: Iterable[StateNamespace]) -> None:
    seen: list[StateNamespace] = []
    for namespace in namespaces:
        if not isinstance(namespace, StateNamespace):
            raise StateNamespaceError(
                "STATE_NAMESPACE_INVALID",
                "namespace collection must contain StateNamespace values",
            )
        expected = StateNamespaceResolver().resolve(
            StateNamespaceRequest(
                ownership=namespace.ownership,
                state_key=namespace.state_key,
                identities=dict(namespace.identities),
            )
        )
        if namespace != expected:
            raise StateNamespaceError(
                "STATE_NAMESPACE_INVALID",
                "namespace does not match the canonical resolver result",
                {"relative_path": namespace.relative_path},
            )
        for previous in seen:
            _validate_namespace_pair(previous, expected)
        seen.append(expected)


__all__ = ["StateNamespaceResolver", "classify_relative_namespace", "validate_namespace_uniqueness"]
