# Change Specification: Post-Merge Project Field Commissioning

- **Change ID**: `227-post-merge-project-field-commissioning`
- **Status**: Approved for implementation
- **Risk Profile**: rigorous

## Outcome

Add a bounded canonical field-only mode to the existing registered GitHub Project schema commissioner so #419's manifest-declared live-verification fields can be provisioned and verified independently of unrelated #409 saved-view drift. Preserve the existing full-schema all-or-nothing safety preflight and expose no arbitrary Project administration.

## Authority and scope

- Authority: `AGENTS.md` > `docs/TRUST-MODEL.md` > `SPEC.md`; #419 defines the commissioning outcome and Change 226 defines canonical Work field authority.
- Provider authority remains the registered `GitHubProjectSchemaClient` and central project registry binding.
- Owned source/test/documentation paths are exactly those declared in `scope.json`.
- #409 owns saved-view semantic drift. #437 remains On Hold and is not a dependency.

## Requirements

- **REQ-001 — Preserve full mode:** Existing `kis_github_commission_registered_project_schema` behavior remains the default. Unsupported existing view sort/group drift must still abort before any field or view mutation.
- **REQ-002 — Bounded fields mode:** The same operation may accept only a fixed `scope` enum of `full` or `fields`; omitted scope means `full`. `fields` may act only on fields/options already declared by the canonical manifest.
- **REQ-003 — No arbitrary administration:** Callers cannot supply field names, GraphQL, option payloads, view configuration, or other provider administration inputs.
- **REQ-004 — Field preflight:** Before the first field mutation, reject every deterministically known field blocker, including type mismatch, missing uncreatable built-in fields, unsupported custom field kinds, and invalid single-select creation requirements.- **REQ-005 — Scoped verification:** After field creation/option repair, re-read provider truth and require canonical `fields_ready=true`. A fields-only success must report `scope=fields`, `fields_ready=true`, and must not claim that unrelated views are ready.
- **REQ-006 — Idempotent recovery:** Re-running fields mode after an acknowledgement loss or partial provider-side application must converge from provider readback without duplicating fields or options.
- **REQ-007 — Capability contract:** The existing discoverable approval-gated virtual operation remains the only mutation surface; capability metadata and dispatcher validation must expose/reject the fixed scope contract deterministically.
- **REQ-008 — Live #419 proof:** After merge and runtime refresh, invoking fields mode for the registered Work Management Project must provision the three Change 226 fields while #409 view drift remains independently visible.

## Acceptance

1. **Given** an existing unsupported view `sort_by` or grouping mismatch, **when** default/full commissioning runs, **then** it refuses before any mutation exactly as today.
2. **Given** the same unrelated view mismatch and missing canonical fields, **when** fields-only commissioning runs, **then** only manifest-declared missing fields/options are mutated and no view mutation is attempted.
3. **Given** a deterministic field blocker, **when** fields-only commissioning is requested, **then** the operation refuses before its first mutation.
4. **Given** all canonical fields are present after apply, **when** provider truth is re-read, **then** the scoped result reports field readiness without representing view readiness as complete.
5. Operation/capability schemas reject unknown scope values and all arbitrary administration inputs.
6. Focused tests, scope check, exact diff check, required review, canonical repository verification, and exact-head GitHub Actions pass.
7. Live post-merge invocation proves the three #419 fields exist; `project_management_schema_status` may remain `views_ready=false` solely for #409-owned drift.

## Risks and recovery

- Risk: weakening the existing atomic full-schema preflight. Mitigation: retain the full path and its regression test unchanged in semantics.
- Risk: partial provider application after a network/acknowledgement failure. Recovery is additive/idempotent re-read and retry; no deletion is introduced.
- Risk: scoped success being mistaken for full Project readiness. Mitigation: return explicit `scope`, `fields_ready`, and non-affirmative view readiness.

## Out of scope

- Repairing or recreating saved views (#409).
- Post-merge classifier, commissioning-issue creation, commissioning runner, or backfill logic; those remain later #419 slices.
- #437 execution-window policy.
- Field deletion, view deletion, arbitrary GraphQL, or general Project administration.