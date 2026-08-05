# Change Specification: Discover Final Integration

- **Change ID**: `037-discover-final-integration`
- **Status**: Approved
- **Risk Profile**: rigorous

## Outcome

Complete the approved bounded public Discover surface with exactly three operations—`inspect_project`, `inspect_change`, and `get_code_context`—using the existing server registration seams and internal services, without overlapping active ownership of `server.py`, `SPEC.md`, or `docs/OPERATIONS.md`.

## Authority and scope

- Authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, and `docs/DISCOVER-MODULE-PRODUCT-SPEC.md`.
- Runtime integration is owned entirely within `src/kis_mcp/discover/tools.py` and `src/kis_mcp/discover/service.py`; `server.py` already invokes these registration seams.
- Public contract tests are owned in the declared Discover test files.
- Discover product-spec status and dedicated integration documentation are owned here.
- Active change `035-llm-capability` owns `src/kis_mcp/server.py`, `SPEC.md`, and `docs/OPERATIONS.md`; this change must not touch them.

## Requirements

- **REQ-001**: `register_discover_tools` must register exactly `inspect_project` and `get_code_context`, both read-only, non-destructive, idempotent, and closed-world.
- **REQ-002**: `InspectProjectService` must remain the server-created façade and delegate code-context requests to `ContextBrokerService` with the same configured boundary and Discover settings.
- **REQ-003**: `get_code_context` must accept an explicit project, task, and complete explicit budget; it must construct the existing version-1 request contract and return the existing version-1 response contract.
- **REQ-004**: Structural request and Discover errors for all public Discover operations must be normalized as deterministic JSON `ToolError` payloads without hard-rule codes.
- **REQ-005**: `inspect_change` must expose every already-supported bounded source: `working_tree`, `staged`, `commit`, `range`, and `branch`, with optional `commit_ref`, `base_ref`, and `head_ref` validated by the existing strict contract.
- **REQ-006**: Existing one-argument `inspect_change(path)` calls must remain compatible and default to `working_tree`.
- **REQ-007**: Server composition through the unchanged existing registration seams must expose the public three-tool Discover surface when mounted, without adding provider admission or project catalog as additional public tools.
- **REQ-008**: End-to-end tests must prove exact tool names, annotations, request delegation, structural-error normalization, server composition, and preservation of internal-only provider admission/project catalog services.
- **REQ-009**: Update the Discover product specification and dedicated integration documentation to distinguish completed public runtime, internal evidence services, known provider limits, and active shared-document ownership.

## Acceptance

1. A local registration server exposes exactly `inspect_project` and `get_code_context` from `register_discover_tools`.
2. The unchanged top-level server composition exposes `inspect_project`, `inspect_change`, and `get_code_context` through its existing registration/mount seams.
3. `get_code_context` delegates the exact `GetCodeContextRequest`, including explicit budget values, and returns its structured response.
4. Invalid context budgets/tasks/projects and invalid change source/ref combinations return deterministic structural `ToolError` JSON without `HR-*` codes.
5. `inspect_change` accepts every supported source shape and preserves the working-tree default.
6. Provider admission and project catalog remain internal services and are not added to the public tool list.
7. Existing Discover behavior, schemas, deterministic tests, and full repository verification remain green.
8. No change is made to active 035-owned files or policy/settings authority.

## Risks and recovery

- Risk: broadening tool signatures can break existing callers.
- Mitigation: retain current defaults and existing parameter names; add only optional source/ref fields and explicit context budget fields.
- Risk: facade composition can create circular imports.
- Mitigation: use a narrow method-local or module-level ContextBroker dependency from `service.py`; no server import is introduced.
- Risk: exact tool-count assertions can drift when mounted providers change.
- Mitigation: assert Discover-owned registration surfaces separately and assert membership, not unrelated provider totals, at top-level server composition.
- Recovery: revert the implementation commit. No persistent state, policy, settings, credentials, provider installation, network behavior, or schema migration is introduced.

## Out of scope

- Changes to `server.py`, `SPEC.md`, or `docs/OPERATIONS.md` while owned by active change 035.
- Public provider-admission or project-catalog tools.
- Provider installation, approval, activation, execution, semantic providers, background indexing, or remote evidence.
