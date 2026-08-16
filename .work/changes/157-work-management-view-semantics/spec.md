# Change Specification: Work Management View Semantics

- **Change ID**: `157-work-management-view-semantics`
- **Status**: Approved by operator instruction to finish Work Management commissioning
- **Complexity**: `medium`
- **Risk Triggers**: `external_action`, `migration`, `public_contract`

## Outcome

Complete Work Management commissioning by making all 12 canonical GitHub Project views carry executable semantics and by refusing `views_ready=true` when those semantics drift.

## Authority and scope

- Authorities: `AGENTS.md`, root `SPEC.md`, `.work/programmes/work-management/target-spec.md`, the canonical Project schema manifest, GitHub issue #270, and current GitHub Project view API contracts.
- Preserve the existing registered Project, item identities, field values, and the additive/no-delete commissioning boundary.
- Do not touch `SPEC.md` or `docs/OPERATIONS.md` while active change 156 owns those paths.
- No overlap with coordinator change 150 or review-safety change 156.

## Requirements

- **REQ-001**: Each manifest view MUST declare an exact filter plus bounded visible-field, sort/group, and board-column configuration where applicable.
- **REQ-002**: View configuration MUST reference Project fields by canonical name; commissioning resolves those names to live field IDs only after the field snapshot is complete.
- **REQ-003**: Existing canonical views MUST be updated in place for API-supported mutable semantics; they MUST NOT be deleted/recreated.
- **REQ-004**: Missing canonical views MUST be created with their complete supported semantics in one bounded fixed-shape operation.
- **REQ-005**: A post-mutation re-read MUST compare name, layout, filter, visible fields, sorting, grouping, and board vertical grouping for every configured semantic dimension.
- **REQ-006**: `project_management_schema_status` MUST consume semantic view observations and return `views_ready=false` for any missing or mismatched declared semantic dimension.- **REQ-007**: Existing legacy Status options may remain for history, but canonical view filters MUST use only current command-plane lifecycle values and must not surface legacy `Todo` / `In Progress` as canonical view semantics.
- **REQ-008**: The bounded commissioner MUST continue to expose no caller-supplied API query/path/token and no Project/view deletion.
- **REQ-009**: Long-lived Work Management programme/commissioning records MUST be reconciled from the obsolete provider-gap state to the post-#270 semantic commissioning state.

## Acceptance

1. `01 Inbox` is filtered to `Status=Inbox` rather than displaying the unfiltered portfolio.
2. `05 Specification Slices`, `06 Decisions`, `07 Assumptions and Risks`, `08 Holds and Deferred`, `09 Reviews and Findings`, `10 Verification`, `11 Documentation and Closeout`, and `12 Completed` have filters matching their declared purposes.
3. `03 Delivery Board` is a board using Status as its board-column grouping when the live API exposes that configuration.
4. Schema comparison reports a named view drift reason when any declared filter/layout/display semantic differs.
5. Recommissioning repairs all API-supported view drift in place, then a fresh re-read returns `views_ready=true` with no unverified/mismatched views.
6. Exact-head CI, governed merge, fresh-runtime commissioning, issue #270 completion, and safe cleanup all succeed before this work is called closed.

## Risks and recovery

- GitHub Project view APIs are newly expanded and may expose some dimensions as read-only. Any unsupported mutable dimension must fail explicitly rather than be silently treated as ready.
- View updates are non-destructive metadata changes. Recovery is an idempotent rerun from the checked-in manifest; no view deletion path is introduced.

## Out of scope

- Enabling native/custom Project automation, intake mutation, or review-import mutation.
- Removing legacy Status options or rewriting historical Project items solely for cosmetic cleanup.
- Native GitHub dependency relationships replacing the commissioned `Blocked By` evidence field.
