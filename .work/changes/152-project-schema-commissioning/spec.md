# Change Specification: Project Schema Commissioning

- **Change ID**: `152-project-schema-commissioning`
- **Status**: Approved for implementation by operator request to close `kis-mcp#142`
- **Complexity**: `medium` under repository governance; additive risk triggers cover security/provider/schema concerns

## Outcome

Provision and verify the authoritative Work Management Project schema through one bounded registered-GitHub commissioning path, without arbitrary GraphQL or a second Project provider.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `docs/OPERATIONS.md`, `settings/work-management/github-project-schema.json`, and GitHub issue `#142`.
- The existing official GitHub MCP adapter remains the normal Project read/item-update provider.
- The existing registered-GitHub exact-operation boundary owns the new approval-gated schema commissioning mutation.
- No policy rule changes; ordinary Work HR-002 remains unchanged.
- No overlap with active change `148-project-created-field-read`; `adapter.py` remains untouched.

## Requirements

- **REQ-001**: Add one strict approval-gated operation that resolves only a centrally registered GitHub Project binding and the canonical schema manifest.
- **REQ-002**: Create only missing manifest-declared Project fields and views; expose no caller-supplied GraphQL, REST path, field definition, view definition, or token.
- **REQ-003**: Preserve existing single-select option IDs when adding missing options so existing item values are not cleared.
- **REQ-004**: Fail closed on incompatible existing field types instead of destructive migration.
- **REQ-005**: Support manifest field kinds required by Project #1: text, date, single-select, and iteration; built-in repository fields are verified rather than recreated.
- **REQ-006**: Create missing manifest views with the minimal manifest-owned semantics; do not invent filters or hidden business rules.
- **REQ-007**: Re-read the Project after mutation and report success only when manifest fields/options and view names are all observed.
- **REQ-008**: Extend `project_management_schema_status` to consume bounded view inventory when the backend provides it; `views_ready` must become evidence-based rather than permanently unknown.
- **REQ-009**: Keep normal reconciliation/item operations delegated to the official GitHub MCP adapter.
- **REQ-010**: Return credential-free bounded commissioning evidence suitable for issue/project closeout.

## Acceptance

1. **Given** a registered Project with the current sparse schema, **when** commissioning is approved, **then** only missing canonical fields/options/views are created or extended.
2. **Given** existing Status options and item values, **when** missing options are added, **then** existing option IDs are supplied back to GitHub and preserved.
3. **Given** an incompatible existing field type, **when** commissioning runs, **then** it fails before attempting destructive type replacement.
4. **Given** successful commissioning, **when** `project_management_schema_status` is rerun, **then** `fields_ready=true`, `views_ready=true`, and `ready=true`.
5. **Given** the commissioned command plane, **when** queue/claim/transition operations are exercised, **then** required Priority/Effort/Status semantics are available without source-issue metadata duplication.
6. Repository focused checks, scope check, required reviews, exact-head CI, landing, runtime commissioning, and issue closeout evidence all succeed.

## Risks and recovery

- Risk: Project schema mutation can alter durable operational state. Mitigation: create-only behavior, option-ID preservation, type mismatch refusal, exact registered target, approval gate, and post-mutation verification.
- Risk: partial commissioning if GitHub rejects a later mutation. Recovery: operation is idempotent; rerun reads current state and applies only still-missing manifest elements.
- Risk: iteration field requires initial cadence configuration not represented in the manifest. Use one documented KIS default only when creating the missing field; never rewrite an existing iteration field.
- Recovery from incorrect newly created metadata is a supervised GitHub Project administrative action outside this bounded operation; the operation itself exposes no delete path.

## Out of scope

- Arbitrary GraphQL/REST passthrough or general GitHub Project administration.
- Project/item deletion, field deletion, destructive field-type conversion, or view deletion.
- Adding a second general Project provider or changing the three Work hard rules.
- GitHub MCP provider version upgrade (`#148` remains independent).
