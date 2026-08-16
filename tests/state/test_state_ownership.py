from __future__ import annotations
import json
from dataclasses import replace
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator
from kis_mcp.state import APPROVED_PROJECT_BOUNDARY, APPROVED_STATE_ROOT, OWNERSHIP_SPECS, StateNamespaceError, StateNamespaceErrorCode, StateNamespaceRequest, StateNamespaceResolver, StateOwnershipClass, derive_change_source_id, derive_worktree_source_id, state_ownership_contract, validate_namespace_uniqueness
from kis_mcp.state.contract import FINGERPRINT_CONTRACT, IDENTITY_CONTRACT, SOURCE_IDENTITY, _load_contract, _load_json_object, _validate_contract_document
from kis_mcp.state.resolver import _validate_namespace_pair
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPOSITORY_ROOT / 'contracts' / 'state' / 'state-ownership.contract.json'
SCHEMA_PATH = REPOSITORY_ROOT / 'contracts' / 'state' / 'state-ownership.contract.schema.json'
REQUEST_SCHEMA_PATH = REPOSITORY_ROOT / 'contracts' / 'state' / 'state-namespace-request.schema.json'
RESULT_SCHEMA_PATH = REPOSITORY_ROOT / 'contracts' / 'state' / 'state-namespace-result.schema.json'
ERROR_SCHEMA_PATH = REPOSITORY_ROOT / 'contracts' / 'state' / 'state-namespace-error.schema.json'
PROJECTS_PATH = REPOSITORY_ROOT / 'settings' / 'projects.settings.json'

def _request(ownership: StateOwnershipClass, *, state_key: str | None='proof', expected: dict[str, str] | None=None, **identities: str) -> StateNamespaceRequest:
    return StateNamespaceRequest(ownership=ownership, state_key=state_key, identities=identities, expected_identities=expected)

def _error_code(exc: pytest.ExceptionInfo[StateNamespaceError]) -> str:
    return exc.value.code

def test_loaded_contract_subcontracts_are_immutable() -> None:
    with pytest.raises(TypeError):
        SOURCE_IDENTITY['worktree_prefix'] = 'other-'
    with pytest.raises(TypeError):
        IDENTITY_CONTRACT['logical_id']['pattern'] = '^other$'
    with pytest.raises(TypeError):
        FINGERPRINT_CONTRACT['canonical_json']['sort_keys'] = False

def test_machine_contract_matches_schema_and_python_projection() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    checked_in = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(checked_in)) == []
    assert checked_in == state_ownership_contract()
    numeric_equivalent = json.loads(json.dumps(checked_in))
    numeric_equivalent['schema_version'] = 1.0
    assert list(validator.iter_errors(numeric_equivalent)) == []
    for invalid_version in (True, False, '1', 2):
        mutation = json.loads(json.dumps(checked_in))
        mutation['schema_version'] = invalid_version
        assert list(validator.iter_errors(mutation))

    structurally_invalid = []
    mutation = json.loads(json.dumps(checked_in))
    mutation['project_boundary'] = 'Projects'
    structurally_invalid.append(mutation)
    mutation = json.loads(json.dumps(checked_in))
    mutation['ownership_classes'][0].pop('scope')
    structurally_invalid.append(mutation)
    mutation = json.loads(json.dumps(checked_in))
    mutation['ownership_classes'][0]['unexpected'] = True
    structurally_invalid.append(mutation)
    mutation = json.loads(json.dumps(checked_in))
    mutation['ownership_classes'][0]['ownership_class'] = 'NOT VALID'
    structurally_invalid.append(mutation)
    mutation = json.loads(json.dumps(checked_in))
    mutation['ownership_classes'][3]['required_identity_keys'] = ['project_id', 'project_id']
    structurally_invalid.append(mutation)
    mutation = json.loads(json.dumps(checked_in))
    mutation['source_identity'].pop('canonical_selection')
    structurally_invalid.append(mutation)
    mutation = json.loads(json.dumps(checked_in))
    mutation['resolver_contract']['error_codes'][0] = 'state_invalid'
    structurally_invalid.append(mutation)
    mutation = json.loads(json.dumps(checked_in))
    mutation['fingerprint_contract']['canonical_json']['separators'] = [',']
    structurally_invalid.append(mutation)
    mutation = json.loads(json.dumps(checked_in))
    mutation['compatibility'].pop('quarantine_root')
    structurally_invalid.append(mutation)
    assert all(list(validator.iter_errors(payload)) for payload in structurally_invalid)

    structurally_valid_semantic_change = json.loads(json.dumps(checked_in))
    structurally_valid_semantic_change['ownership_classes'][3]['namespace_template'] = (
        'projects/{project_id}/other/{state_key}'
    )
    assert list(validator.iter_errors(structurally_valid_semantic_change)) == []

    assert checked_in['state_root'] == APPROVED_STATE_ROOT
    assert checked_in['project_boundary'] == APPROVED_PROJECT_BOUNDARY
    assert [item['ownership_class'] for item in checked_in['ownership_classes']] == [
        item.value for item in StateOwnershipClass
    ]
    assert checked_in['resolver_contract']['error_codes'] == [
        item.value for item in StateNamespaceErrorCode
    ]
    assert [item.to_json_dict() for item in OWNERSHIP_SPECS] == checked_in['ownership_classes']


def test_runtime_contract_loader_rejects_malformed_or_unsupported_contracts() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    checked_in = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    validator = Draft202012Validator(schema)
    _validate_contract_document(checked_in)
    for field in ('schema_version', 'namespace_version'):
        for invalid_version in (True, '1', 1.0, 1.5, 2):
            mutation = json.loads(json.dumps(checked_in))
            mutation[field] = invalid_version
            with pytest.raises(RuntimeError, match='STATE_CONTRACT_INVALID'):
                _validate_contract_document(mutation)
    malformed = json.loads(json.dumps(checked_in))
    malformed['project_boundary'] = 'Projects'
    with pytest.raises(RuntimeError, match='STATE_CONTRACT_INVALID'):
        _validate_contract_document(malformed)
    for index, ownership in enumerate(checked_in['ownership_classes']):
        semantic_drift = json.loads(json.dumps(checked_in))
        semantic_drift['ownership_classes'][index]['namespace_template'] = (
            ownership['namespace_template'] + '/other'
        )
        assert list(validator.iter_errors(semantic_drift)) == []
        with pytest.raises(RuntimeError, match='STATE_CONTRACT_INVALID'):
            _validate_contract_document(semantic_drift)
    semantic_mutations = (
        (('project_boundary',), r'C:\Repos'),
        (('state_root',), r'C:\Projects\.kis-other'),
        (('source_identity', 'git_lookup_required'), True),
        (('identity_contract', 'logical_id', 'max_length'), 127),
        (('fingerprint_contract', 'canonical_json', 'ensure_ascii'), False),
        (('compatibility', 'secrets_root'), r'C:\Projects\.kis-mcp\secrets-v2'),
        (('resolver_contract', 'diagnostic_limits', 'max_fields'), 9),
    )
    for path, value in semantic_mutations:
        semantic_drift = json.loads(json.dumps(checked_in))
        target = semantic_drift
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        assert list(validator.iter_errors(semantic_drift)) == []
        with pytest.raises(RuntimeError, match='STATE_CONTRACT_INVALID'):
            _validate_contract_document(semantic_drift)


def test_runtime_contract_loader_fails_closed_on_file_errors(tmp_path: Path) -> None:
    missing = tmp_path / 'missing.json'
    with pytest.raises(RuntimeError, match='STATE_CONTRACT_UNAVAILABLE'):
        _load_json_object(missing, label='state contract')
    malformed = tmp_path / 'malformed.json'
    malformed.write_text('{', encoding='utf-8')
    with pytest.raises(RuntimeError, match='STATE_CONTRACT_UNAVAILABLE'):
        _load_json_object(malformed, label='state contract')
    invalid_utf8 = tmp_path / 'invalid-utf8.json'
    invalid_utf8.write_bytes(b'\xff')
    with pytest.raises(RuntimeError, match='STATE_CONTRACT_UNAVAILABLE'):
        _load_json_object(invalid_utf8, label='state contract')
    non_object = tmp_path / 'non-object.json'
    non_object.write_text('[]', encoding='utf-8')
    with pytest.raises(RuntimeError, match='STATE_CONTRACT_INVALID'):
        _load_json_object(non_object, label='state contract')
    contract_copy = tmp_path / 'contract.json'
    contract_copy.write_bytes(CONTRACT_PATH.read_bytes())
    assert _load_contract(contract_copy) == json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    with pytest.raises(RuntimeError, match='STATE_CONTRACT_UNAVAILABLE'):
        _load_contract(missing)


@pytest.mark.parametrize(
    'spec',
    OWNERSHIP_SPECS,
    ids=lambda spec: spec.ownership_class.value,
)
def test_every_ownership_class_enforces_its_exact_identity_scope(spec) -> None:
    resolver = StateNamespaceResolver()
    available = {
        'project_id': 'kis-mcp',
        'source_id': derive_change_source_id('163-state-ownership-namespace'),
        'runtime_instance_id': 'operation',
    }
    identities = {key: available[key] for key in spec.required_identity_keys}
    state_key = 'proof' if spec.state_key_required else None
    resolver.resolve(
        StateNamespaceRequest(
            ownership=spec.ownership_class,
            state_key=state_key,
            identities=identities,
        )
    )
    for required_key in spec.required_identity_keys:
        missing_identities = dict(identities)
        missing_identities.pop(required_key)
        with pytest.raises(StateNamespaceError) as missing:
            resolver.resolve(
                StateNamespaceRequest(
                    ownership=spec.ownership_class,
                    state_key=state_key,
                    identities=missing_identities,
                )
            )
        assert _error_code(missing) == 'STATE_IDENTITY_MISSING'
    for forbidden_key in sorted(set(available) - set(spec.required_identity_keys)):
        unexpected_identities = {**identities, forbidden_key: available[forbidden_key]}
        with pytest.raises(StateNamespaceError) as unexpected:
            resolver.resolve(
                StateNamespaceRequest(
                    ownership=spec.ownership_class,
                    state_key=state_key,
                    identities=unexpected_identities,
                )
            )
        assert _error_code(unexpected) == 'STATE_IDENTITY_UNEXPECTED'


def test_ownership_semantics_are_independently_locked_by_behavior() -> None:
    resolver = StateNamespaceResolver()
    source_id = derive_change_source_id('163-state-ownership-namespace')
    cases = (
        (StateOwnershipClass.GLOBAL_AUTHORITY, 'registry', {}, 'global\\authority\\registry'),
        (StateOwnershipClass.GLOBAL_CACHE, 'provider-builds', {}, 'global\\cache\\provider-builds'),
        (StateOwnershipClass.SHARED_AUTH, 'vault', {}, 'global\\auth\\vault'),
        (StateOwnershipClass.PROJECT_SPECIFIC, 'coordinator', {'project_id': 'kis-mcp'}, 'projects\\kis-mcp\\state\\coordinator'),
        (StateOwnershipClass.WORKTREE_SPECIFIC, 'execution', {'project_id': 'kis-mcp', 'source_id': source_id}, f'projects\\kis-mcp\\sources\\{source_id}\\state\\execution'),
        (StateOwnershipClass.RUNTIME_INSTANCE_SPECIFIC, 'liveness', {'runtime_instance_id': 'operation'}, 'runtime\\operation\\state\\liveness'),
        (StateOwnershipClass.EPHEMERAL, 'process', {'runtime_instance_id': 'operation', 'project_id': 'kis-mcp', 'source_id': source_id}, f'runtime\\operation\\projects\\kis-mcp\\sources\\{source_id}\\ephemeral\\process'),
        (StateOwnershipClass.RECONSTRUCTIBLE_CACHE, 'discover-derived', {'project_id': 'kis-mcp', 'source_id': source_id}, f'projects\\kis-mcp\\sources\\{source_id}\\reconstructible\\discover-derived'),
        (StateOwnershipClass.DURABLE_EVIDENCE, 'review', {'project_id': 'kis-mcp', 'source_id': source_id}, f'projects\\kis-mcp\\sources\\{source_id}\\evidence\\review'),
        (StateOwnershipClass.RECOVERY_QUARANTINE, None, {}, 'quarantine'),
    )
    for ownership, state_key, identities, expected_relative in cases:
        resolved = resolver.resolve(
            StateNamespaceRequest(
                ownership=ownership,
                state_key=state_key,
                identities=identities,
            )
        )
        assert resolved.relative_path == expected_relative


def test_machine_contract_publishes_wire_identity_fingerprint_and_error_contracts() -> None:
    contract = state_ownership_contract()
    identity = contract['identity_contract']
    resolver_contract = contract['resolver_contract']
    fingerprint = contract['fingerprint_contract']
    assert contract['namespace_version'] == 1
    assert identity['logical_id']['pattern'] == '^[a-z0-9]+(?:-[a-z0-9]+)*$'
    assert identity['logical_id']['max_length'] == 128
    assert identity['logical_id']['canonicalization'] == ['strip', 'casefold']
    assert identity['governed_change_id']['pattern'] == '^[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$'
    assert identity['source_id']['pattern'].startswith('^')
    assert identity['worktree_root']['boundary'] == APPROVED_PROJECT_BOUNDARY
    assert resolver_contract['request_schema'] == 'state-namespace-request.schema.json'
    assert resolver_contract['result_schema'] == 'state-namespace-result.schema.json'
    assert resolver_contract['error_schema'] == 'state-namespace-error.schema.json'
    assert resolver_contract['diagnostic_limits'] == {'max_fields': 8, 'max_key_length': 64, 'max_value_length': 160}
    assert resolver_contract['error_codes'] == [item.value for item in StateNamespaceErrorCode]
    source_identity = contract['source_identity']
    assert source_identity['governed_worktree_suffix'] == '\\.work\\worktrees\\<governed-change-id>'
    assert source_identity['canonical_selection'] == 'governed-worktree-change-id-otherwise-worktree-root-digest'
    assert fingerprint['algorithm'] == 'sha256'
    assert fingerprint['encoding'] == 'utf-8'
    assert fingerprint['document_fields'] == [
        'schema_version',
        'namespace_version',
        'ownership_class',
        'state_key',
        'identities',
        'relative_path',
    ]
    assert fingerprint['canonical_json']['sort_keys'] is True
    assert fingerprint['canonical_json']['trailing_newline'] is True
    vector = fingerprint['test_vector']
    assert len(vector['identity_fingerprint']) == 64
    vector_document = vector['document']
    assert vector_document['namespace_version'] == contract['namespace_version']
    resolved_vector = StateNamespaceResolver().resolve(StateNamespaceRequest(ownership=vector_document['ownership_class'], state_key=vector_document['state_key'], identities=vector_document['identities']))
    assert resolved_vector.relative_path == vector_document['relative_path']
    assert resolved_vector.identity_fingerprint == vector['identity_fingerprint']
    assert derive_change_source_id('163-state-ownership-namespace').startswith(contract['source_identity']['change_prefix'])
    assert derive_worktree_source_id('C:\\Projects\\kis-mcp').startswith(contract['source_identity']['worktree_prefix'])

def test_public_request_result_and_error_serializations_validate_against_schemas() -> None:
    request_schema = json.loads(REQUEST_SCHEMA_PATH.read_text(encoding='utf-8'))
    result_schema = json.loads(RESULT_SCHEMA_PATH.read_text(encoding='utf-8'))
    error_schema = json.loads(ERROR_SCHEMA_PATH.read_text(encoding='utf-8'))
    resolver = StateNamespaceResolver()
    source_id = derive_change_source_id('163-state-ownership-namespace')
    request = _request(StateOwnershipClass.DURABLE_EVIDENCE, state_key='verification', expected={'project_id': 'kis-mcp', 'source_id': source_id}, project_id='kis-mcp', source_id=source_id)
    result = resolver.resolve(request)
    error = StateNamespaceError(StateNamespaceErrorCode.STATE_IDENTITY_STALE, 'stale proof', {'mismatched_keys': 'source_id'})
    request_validator = Draft202012Validator(request_schema)
    result_validator = Draft202012Validator(result_schema)
    error_validator = Draft202012Validator(error_schema)
    request_payload = request.to_json_dict()
    result_payload = result.to_json_dict()
    error_payload = error.to_json_dict()
    assert list(request_validator.iter_errors(request_payload)) == []
    assert list(result_validator.iter_errors(result_payload)) == []
    assert list(error_validator.iter_errors(error_payload)) == []
    for validator, payload in (
        (request_validator, request_payload),
        (result_validator, result_payload),
        (error_validator, error_payload),
    ):
        assert list(validator.iter_errors({**payload, 'schema_version': 1.0})) == []
        for invalid_version in (True, False, '1', 2):
            invalid_payload = {**payload, 'schema_version': invalid_version}
            assert list(validator.iter_errors(invalid_payload))
    assert StateNamespaceRequest.from_json_dict(request_payload) == request
    numeric_version_request = StateNamespaceRequest.from_json_dict(
        {**request_payload, 'schema_version': 1.0}
    )
    assert numeric_version_request.to_json_dict()['schema_version'] == 1
    for invalid_wire in (
        {**request_payload, 'unexpected': True},
        {key: value for key, value in request_payload.items() if key != 'state_key'},
        {**request_payload, 'ownership_class': ' DURABLE-EVIDENCE '},
        *({**request_payload, 'schema_version': value} for value in (True, False, '1', 2)),
    ):
        with pytest.raises(StateNamespaceError) as invalid_request:
            StateNamespaceRequest.from_json_dict(invalid_wire)
        assert _error_code(invalid_request) == 'STATE_REQUEST_INVALID'
    result_payload = result.to_json_dict()
    assert result.namespace_version == state_ownership_contract()['namespace_version']
    assert result_payload['namespace_version'] == result.namespace_version
    assert list(result_validator.iter_errors(result_payload)) == []
    assert list(Draft202012Validator(error_schema).iter_errors(error.to_json_dict())) == []
    normalized = StateNamespaceRequest(ownership=' PROJECT-SPECIFIC ', state_key=' Coordinator ', identities={'project_id': ' KIS-MCP '}).to_json_dict()
    assert normalized['ownership_class'] == 'project-specific'
    assert normalized['state_key'] == 'coordinator'
    assert normalized['identities'] == {'project_id': 'kis-mcp'}
    assert list(request_validator.iter_errors(normalized)) == []
    invalid_requests = ({'schema_version': 1, 'ownership_class': 'project-specific', 'state_key': 'proof', 'identities': {}, 'expected_identities': None}, {'schema_version': 1, 'ownership_class': 'global-cache', 'state_key': 'proof', 'identities': {'project_id': 'kis-mcp'}, 'expected_identities': None}, {'schema_version': 1, 'ownership_class': 'recovery-quarantine', 'state_key': 'unexpected', 'identities': {}, 'expected_identities': None})
    assert all((list(request_validator.iter_errors(payload)) for payload in invalid_requests))
    invalid_result = result.to_json_dict()
    invalid_result['identities'] = {}
    assert list(result_validator.iter_errors(invalid_result))
    for invalid_relative in ('..\\outside', 'C:\\absolute'):
        invalid_result = result.to_json_dict()
        invalid_result['relative_path'] = invalid_relative
        assert list(result_validator.iter_errors(invalid_result))
    redundant_absolute_path = result.to_json_dict()
    redundant_absolute_path['path'] = result.path
    assert list(result_validator.iter_errors(redundant_absolute_path))

def test_request_defensively_copies_identity_mappings() -> None:
    identities = {'project_id': 'kis-mcp'}
    expected = {'project_id': 'kis-mcp'}
    request = StateNamespaceRequest(ownership=StateOwnershipClass.PROJECT_SPECIFIC, state_key='coordinator', identities=identities, expected_identities=expected)
    identities['project_id'] = 'commodity'
    expected['project_id'] = 'commodity'
    payload = request.to_json_dict()
    assert payload['identities'] == {'project_id': 'kis-mcp'}
    assert payload['expected_identities'] == {'project_id': 'kis-mcp'}
    assert StateNamespaceResolver().resolve(request).identities == (('project_id', 'kis-mcp'),)

def test_request_rejects_non_mapping_identity_containers_with_typed_errors() -> None:
    for invalid in (None, 1, [('project_id',)]):
        with pytest.raises(StateNamespaceError) as error:
            StateNamespaceRequest(ownership=StateOwnershipClass.PROJECT_SPECIFIC, state_key='coordinator', identities=invalid)
        assert _error_code(error) == 'STATE_IDENTITY_INVALID'
    with pytest.raises(StateNamespaceError) as expected_error:
        StateNamespaceRequest(ownership=StateOwnershipClass.PROJECT_SPECIFIC, state_key='coordinator', identities={'project_id': 'kis-mcp'}, expected_identities=1)
    assert _error_code(expected_error) == 'STATE_IDENTITY_INVALID'

def test_project_source_and_runtime_namespaces_are_deterministic_and_isolated() -> None:
    resolver = StateNamespaceResolver()
    projects = json.loads(PROJECTS_PATH.read_text(encoding='utf-8'))['projects']
    project_ids = {item['project_id'] for item in projects}
    assert {'kis-mcp', 'commodity'} <= project_ids
    worktree_a = derive_worktree_source_id('C:\\Projects\\kis-mcp\\.work\\worktrees\\163-state-ownership-namespace')
    worktree_b = derive_worktree_source_id('C:\\Projects\\commodity\\.work\\worktrees\\sample')
    kis = resolver.resolve(_request(StateOwnershipClass.DURABLE_EVIDENCE, state_key='verification', project_id='kis-mcp', source_id=worktree_a))
    same = resolver.resolve(_request(StateOwnershipClass.DURABLE_EVIDENCE, state_key='verification', project_id='kis-mcp', source_id=worktree_a))
    commodity = resolver.resolve(_request(StateOwnershipClass.DURABLE_EVIDENCE, state_key='verification', project_id='commodity', source_id=worktree_b))
    runtime = resolver.resolve(_request(StateOwnershipClass.RUNTIME_INSTANCE_SPECIFIC, state_key='liveness', runtime_instance_id='development'))
    assert same == kis
    assert kis.path == APPROVED_STATE_ROOT + '\\projects\\kis-mcp\\sources\\' + worktree_a + '\\evidence\\verification'
    assert commodity.path != kis.path
    assert runtime.path == APPROVED_STATE_ROOT + '\\runtime\\development\\state\\liveness'
    validate_namespace_uniqueness((kis, commodity, runtime))

def test_global_classes_cannot_acquire_scoped_identity_and_scoped_classes_require_it() -> None:
    resolver = StateNamespaceResolver()
    global_namespace = resolver.resolve(_request(StateOwnershipClass.GLOBAL_CACHE, state_key='uv-packages'))
    assert global_namespace.path == APPROVED_STATE_ROOT + '\\global\\cache\\uv-packages'
    assert not global_namespace.relative_path.casefold().startswith('projects\\')
    with pytest.raises(StateNamespaceError) as unexpected:
        resolver.resolve(_request(StateOwnershipClass.GLOBAL_CACHE, state_key='uv-packages', project_id='kis-mcp'))
    assert _error_code(unexpected) == 'STATE_IDENTITY_UNEXPECTED'
    with pytest.raises(StateNamespaceError) as missing:
        resolver.resolve(_request(StateOwnershipClass.PROJECT_SPECIFIC, state_key='coordinator'))
    assert _error_code(missing) == 'STATE_IDENTITY_MISSING'
    source_id = derive_change_source_id('163-state-ownership-namespace')
    worktree_namespace = resolver.resolve(_request(StateOwnershipClass.WORKTREE_SPECIFIC, state_key='execution', project_id='kis-mcp', source_id=source_id))
    assert '\\projects\\kis-mcp\\sources\\change-163-state-ownership-namespace\\' in worktree_namespace.path

def test_linked_worktree_normalization_is_stable_without_git_lookup() -> None:
    canonical = derive_worktree_source_id('C:\\Projects\\kis-mcp\\.work\\worktrees\\feature-a')
    equivalent = derive_worktree_source_id('c:/projects/KIS-MCP/.work/worktrees/feature-a/.')
    distinct = derive_worktree_source_id('C:\\Projects\\kis-mcp\\.work\\worktrees\\feature-b')
    governed = derive_worktree_source_id('C:\\Projects\\kis-mcp\\.work\\worktrees\\163-state-ownership-namespace')
    nested = derive_worktree_source_id('C:\\Projects\\kis-mcp\\nested\\.work\\worktrees\\163-state-ownership-namespace')
    assert canonical == equivalent
    assert canonical.startswith('worktree-')
    assert len(canonical) == len('worktree-') + 64
    assert distinct != canonical
    assert governed == derive_change_source_id('163-state-ownership-namespace')
    assert nested.startswith('worktree-')
    assert nested != governed
    for outside_root in ('C:\\Projects', 'D:\\Other\\feature-a', 'C:\\Projects2\\feature-a', 'C:\\Projects\\..\\Other\\feature-a'):
        with pytest.raises(StateNamespaceError) as outside:
            derive_worktree_source_id(outside_root)
        assert _error_code(outside) == 'STATE_SOURCE_IDENTITY_INVALID'
    for relative in ('kis-mcp', 'C:kis-mcp', '\\kis-mcp'):
        with pytest.raises(StateNamespaceError) as invalid:
            derive_worktree_source_id(relative)
        assert _error_code(invalid) == 'STATE_SOURCE_IDENTITY_INVALID'

def test_change_source_identity_requires_governed_change_id() -> None:
    assert derive_change_source_id('163-state-ownership-namespace') == 'change-163-state-ownership-namespace'
    for invalid_change_id in ('coordinator', 'main', '16-change', '016-Change'):
        with pytest.raises(StateNamespaceError) as invalid:
            derive_change_source_id(invalid_change_id)
        assert _error_code(invalid) == 'STATE_SOURCE_IDENTITY_INVALID'

def test_stale_and_malformed_identity_fail_with_bounded_diagnostics() -> None:
    resolver = StateNamespaceResolver()
    current_source = derive_change_source_id('163-state-ownership-namespace')
    stale_source = derive_change_source_id('162-older-state-change')
    with pytest.raises(StateNamespaceError) as stale:
        resolver.resolve(_request(StateOwnershipClass.DURABLE_EVIDENCE, state_key='review', expected={'project_id': 'kis-mcp', 'source_id': current_source}, project_id='kis-mcp', source_id=stale_source))
    assert _error_code(stale) == 'STATE_IDENTITY_STALE'
    diagnostic = stale.value.to_json_dict()
    assert len(diagnostic['diagnostics']) <= 8
    assert all((len(value) <= 160 for value in diagnostic['diagnostics'].values()))
    with pytest.raises(StateNamespaceError) as malformed:
        resolver.resolve(_request(StateOwnershipClass.PROJECT_SPECIFIC, state_key='coordinator', project_id='../kis-mcp'))
    assert _error_code(malformed) == 'STATE_IDENTITY_INVALID'
    with pytest.raises(StateNamespaceError) as malformed_key:
        resolver.resolve(_request(StateOwnershipClass.PROJECT_SPECIFIC, state_key='../coordinator', project_id='kis-mcp'))
    assert _error_code(malformed_key) == 'STATE_KEY_INVALID'

def test_expected_identity_contract_rejects_missing_extra_and_global_scope() -> None:
    resolver = StateNamespaceResolver()
    source_id = derive_change_source_id('163-state-ownership-namespace')
    with pytest.raises(StateNamespaceError) as missing:
        resolver.resolve(_request(StateOwnershipClass.DURABLE_EVIDENCE, expected={'project_id': 'kis-mcp'}, project_id='kis-mcp', source_id=source_id))
    assert _error_code(missing) == 'STATE_IDENTITY_MISSING'
    with pytest.raises(StateNamespaceError) as extra:
        resolver.resolve(_request(StateOwnershipClass.PROJECT_SPECIFIC, expected={'project_id': 'kis-mcp', 'source_id': source_id}, project_id='kis-mcp'))
    assert _error_code(extra) == 'STATE_IDENTITY_UNEXPECTED'
    with pytest.raises(StateNamespaceError) as global_expected:
        resolver.resolve(_request(StateOwnershipClass.GLOBAL_CACHE, expected={'project_id': 'kis-mcp'}))
    assert _error_code(global_expected) == 'STATE_IDENTITY_UNEXPECTED'

def test_error_diagnostics_are_actually_bounded() -> None:
    diagnostics = {f'key-{index}-' + 'k' * 80: 'v' * 240 for index in range(12)}
    error = StateNamespaceError(StateNamespaceErrorCode.STATE_IDENTITY_INVALID, 'invalid identity', diagnostics)
    payload = error.to_json_dict()
    assert len(payload['diagnostics']) == 8
    assert all((len(key) <= 64 for key in payload['diagnostics']))
    assert all((len(value) <= 160 for value in payload['diagnostics'].values()))
    with pytest.raises(ValueError):
        StateNamespaceError('STATE_NOT_A_REAL_CODE', 'invalid')
    with pytest.raises(ValueError):
        StateNamespaceError(StateNamespaceErrorCode.STATE_IDENTITY_INVALID, '   ')

def test_ephemeral_state_requires_runtime_project_and_source_identity() -> None:
    resolver = StateNamespaceResolver()
    source_id = derive_worktree_source_id('C:\\Projects\\kis-mcp\\.work\\worktrees\\feature-a')
    namespace = resolver.resolve(_request(StateOwnershipClass.EPHEMERAL, state_key='process-evidence', runtime_instance_id='development', project_id='kis-mcp', source_id=source_id))
    assert namespace.path == APPROVED_STATE_ROOT + '\\runtime\\development\\projects\\kis-mcp\\sources\\' + source_id + '\\ephemeral\\process-evidence'
    with pytest.raises(StateNamespaceError) as missing_source:
        resolver.resolve(_request(StateOwnershipClass.EPHEMERAL, state_key='process-evidence', runtime_instance_id='development', project_id='kis-mcp'))
    assert _error_code(missing_source) == 'STATE_IDENTITY_MISSING'

def test_quarantine_and_legacy_auth_recovery_anchors_remain_compatible() -> None:
    resolver = StateNamespaceResolver()
    quarantine = resolver.resolve(_request(StateOwnershipClass.RECOVERY_QUARANTINE, state_key=None))
    contract = state_ownership_contract()
    compatibility = contract['compatibility']
    assert quarantine.path == APPROVED_STATE_ROOT + '\\quarantine'
    assert compatibility['quarantine_root'] == quarantine.path
    assert compatibility['secrets_root'] == APPROVED_STATE_ROOT + '\\secrets'
    assert compatibility['github_cli_config_dir'] == 'C:\\Projects\\.mcp-external-state\\gh-config'
    assert compatibility['repo_local_recovery_capsule_pattern'] == '<registered-project>\\.temp\\kis'
    assert compatibility['repo_local_recovery_authoritative'] is False
    assert compatibility['consumer_migration_in_this_slice'] is False

def test_namespace_collision_guard_rejects_same_path_with_different_identity_fingerprint() -> None:
    resolver = StateNamespaceResolver()
    request = _request(StateOwnershipClass.PROJECT_SPECIFIC, state_key='coordinator', project_id='kis-mcp')
    resolved = resolver.resolve(request)
    forged = replace(resolved, identity_fingerprint='f' * 64)
    with pytest.raises(StateNamespaceError) as duplicate:
        resolver.resolve_many((request, request))
    assert _error_code(duplicate) == 'STATE_NAMESPACE_COLLISION'
    with pytest.raises(StateNamespaceError) as collision:
        validate_namespace_uniqueness((resolved, forged))
    assert _error_code(collision) == 'STATE_NAMESPACE_INVALID'
    forged_relative = replace(resolved, relative_path='projects\\kis-mcp\\state\\segment\\..\\coordinator')
    with pytest.raises(StateNamespaceError) as invalid_relative:
        validate_namespace_uniqueness((forged_relative,))
    assert _error_code(invalid_relative) == 'STATE_NAMESPACE_INVALID'
    forged_path = replace(resolved, path='D:\\outside')
    with pytest.raises(StateNamespaceError) as invalid_path:
        validate_namespace_uniqueness((forged_path,))
    assert _error_code(invalid_path) == 'STATE_NAMESPACE_INVALID'
    windows_equivalent = replace(resolved, path=resolved.path.upper().replace('\\', '/') + '/.', identity_fingerprint='e' * 64)
    with pytest.raises(StateNamespaceError) as normalized_collision:
        validate_namespace_uniqueness((resolved, windows_equivalent))
    assert _error_code(normalized_collision) == 'STATE_NAMESPACE_INVALID'

def test_namespace_classes_are_prefix_disjoint_and_guard_ancestor_overlap() -> None:
    resolver = StateNamespaceResolver()
    source_id = derive_change_source_id('163-state-ownership-namespace')
    project_generic = resolver.resolve(_request(StateOwnershipClass.PROJECT_SPECIFIC, state_key='sources', project_id='kis-mcp'))
    worktree_generic = resolver.resolve(_request(StateOwnershipClass.WORKTREE_SPECIFIC, state_key='evidence', project_id='kis-mcp', source_id=source_id))
    runtime_generic = resolver.resolve(_request(StateOwnershipClass.RUNTIME_INSTANCE_SPECIFIC, state_key='projects', runtime_instance_id='operation'))
    evidence = resolver.resolve(_request(StateOwnershipClass.DURABLE_EVIDENCE, state_key='review', project_id='kis-mcp', source_id=source_id))
    assert project_generic.relative_path == 'projects\\kis-mcp\\state\\sources'
    assert worktree_generic.relative_path.endswith('\\state\\evidence')
    assert runtime_generic.relative_path == 'runtime\\operation\\state\\projects'
    validate_namespace_uniqueness((project_generic, worktree_generic, runtime_generic, evidence))
    child = replace(project_generic, relative_path=project_generic.relative_path + '\\nested', path=project_generic.path.upper() + '\\NeStEd\\.', identity_fingerprint='e' * 64)
    with pytest.raises(StateNamespaceError) as overlap:
        _validate_namespace_pair(project_generic, child)
    assert _error_code(overlap) == 'STATE_NAMESPACE_COLLISION'
    with pytest.raises(StateNamespaceError) as noncanonical:
        validate_namespace_uniqueness((project_generic, child))
    assert _error_code(noncanonical) == 'STATE_NAMESPACE_INVALID'

def test_resolved_paths_remain_beneath_fixed_state_root() -> None:
    resolver = StateNamespaceResolver()
    source_id = derive_change_source_id('163-state-ownership-namespace')
    requests = (_request(StateOwnershipClass.GLOBAL_AUTHORITY, state_key='registry'), _request(StateOwnershipClass.GLOBAL_CACHE, state_key='provider-builds'), _request(StateOwnershipClass.SHARED_AUTH, state_key='vault'), _request(StateOwnershipClass.PROJECT_SPECIFIC, state_key='coordinator', project_id='kis-mcp'), _request(StateOwnershipClass.WORKTREE_SPECIFIC, state_key='execution', project_id='kis-mcp', source_id=source_id), _request(StateOwnershipClass.RECONSTRUCTIBLE_CACHE, state_key='discover-derived', project_id='kis-mcp', source_id=source_id), _request(StateOwnershipClass.DURABLE_EVIDENCE, state_key='review', project_id='kis-mcp', source_id=source_id), _request(StateOwnershipClass.RUNTIME_INSTANCE_SPECIFIC, state_key='commissioning', runtime_instance_id='operation'), _request(StateOwnershipClass.EPHEMERAL, state_key='process', runtime_instance_id='operation', project_id='kis-mcp', source_id=source_id), _request(StateOwnershipClass.RECOVERY_QUARANTINE, state_key=None))
    namespaces = resolver.resolve_many(requests)
    assert len(namespaces) == len(requests)
    assert all((item.path.casefold().startswith(APPROVED_STATE_ROOT.casefold() + '\\') for item in namespaces))
