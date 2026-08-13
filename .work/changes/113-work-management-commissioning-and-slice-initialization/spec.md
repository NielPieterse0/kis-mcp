# Change Specification: Work Management Commissioning And Slice Initialization

- **Change ID**: `113-work-management-commissioning-and-slice-initialization`
- **Status**: Approved / active
- **Risk Profile**: rigorous
- **Development level**: Complex — changes shared change-governance schema/CLI behavior, persistent GitHub Project state, and commissioning workflow.
- **Documentation impact**: planned
- **Work Management record**: `SPEC-113`, GitHub issue `#138`

## Outcome

Commission the already-approved Work Management operational projection as far as the bounded GitHub surface permits, backfill changes 110-112, and make prior Work Management initialization evidence mandatory for every newly governed slice.

## Authority and scope

- `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, policy, and `docs/OPERATIONS.md` remain authoritative in that order.
- `.work/programmes/work-management/target-spec.md` remains the approved Work Management programme contract.
- Repository change artifacts and Git history remain authoritative engineering truth; GitHub Project is operational projection only.
- Change 112 is already `112-system-audit-review`; this slice therefore uses the next unique ID, 113.
- Owned files are exactly those declared in `scope.json`; no provider pin, policy rule, or unrelated product surface is changed.

## Requirements

- **REQ-001**: Every newly created governed change MUST carry machine-readable evidence that its Work Management record already exists before `change-workflow new` creates the worktree.
- **REQ-002**: New change scopes MUST use a backward-compatible schema version that records stable Work Management identity without requiring network access during local validation.
- **REQ-003**: Work Management evidence MUST identify project ID, record ID, source repository, source issue/PR number and kind, plus documentation-impact classification.
- **REQ-004**: Historical schema-version-1 change records MUST remain valid; existing changes MUST NOT require retroactive mutation merely to pass governance.
- **REQ-005**: Change 110, 111, and 112 MUST each have a visible GitHub Work Management specification-slice record linked to authoritative repository evidence and projected into Project #1.
- **REQ-006**: Outstanding work discovered from 110/111 MUST be represented as separate visible records rather than keeping completed parent slices falsely open.
- **REQ-007**: Change 113 lifecycle projection MUST be updated as the slice progresses using the currently live Status options until the rich schema is commissioned.
- **REQ-008**: The approved 18-field / 12-view schema gap MUST remain explicitly reported; unsupported GitHub MCP provisioning MUST NOT be bypassed with unrestricted GraphQL or local network access.
- **REQ-009**: Operator-only GitHub UI commissioning steps MUST be documented precisely and kept separate from automated KIS execution.
- **REQ-010**: Current authority, operator guidance, programme state, tests, and change closeout MUST agree with the commissioned state.

## Acceptance

1. **Given** a new change without Work Management evidence, **when** `change-workflow new` runs, **then** it fails before creating a branch or worktree.
2. **Given** valid Work Management evidence, **when** `change-workflow new` runs, **then** the new schema-version-2 `scope.json` records that evidence and the worktree is created normally.
3. **Given** historical schema-version-1 scopes, **when** repository governance validation runs, **then** they remain valid without Work Management metadata.
4. **Given** changes 110, 111, and 112, **when** Project #1 is inventoried, **then** each has a visible source issue/project item with truthful current status and repository traceability.
5. **Given** residual work from 110/111, **when** Work Management is inspected, **then** separate open records expose the rich-schema commissioning gap and provider-status persistence defect.
6. **Given** the current GitHub MCP tool surface, **when** schema commissioning is assessed, **then** unsupported fields/views remain explicit and no unrestricted API bypass is introduced.
7. Focused governance tests, Work Management tests, scope check, specialist review, canonical verification, live Project evidence, exact-head delivery, documentation reconciliation, and safe cleanup are recorded.

## Risks and recovery

- **Risk**: requiring new metadata can break existing automation if compatibility is not versioned. **Recovery**: schema v1 remains accepted; only `new` emits/requires v2 evidence.
- **Risk**: GitHub Project custom-field/view provisioning is not exposed by the approved GitHub MCP. **Recovery**: retain current three-status projection and use a supervised GitHub UI commissioning checklist.
- **Risk**: external Project mutations can partially succeed. **Recovery**: use source issues as stable identities, preview-first reconciliation, idempotency keys, and no delete operations.
- **Risk**: the concurrent 112 audit slice must not be disturbed. **Recovery**: 113 has disjoint owned paths and does not modify 112 artifacts.

## Out of scope

- Generated/code-derived module documentation architecture.
- Docker Hub provider upgrades, Docker Engine control, or fixing the upstream Docker Hub search response.
- Unrestricted GitHub GraphQL/API passthrough or new Work hard rules.
- Retrofitting every historical change before 110 into Work Management.
