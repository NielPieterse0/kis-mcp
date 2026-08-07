# Change Specification: P5 Work Management Automation

- **Change ID:** `057-work-management-automation`
- **Status:** Approved for implementation by operator request on 2026-08-07
- **Risk profile:** Rigorous / Complex
- **Programme phase:** P5

## Outcome

Complete the internal work-management capability with durable review evidence, provider-neutral reconciliation and portfolio status, a bounded GitHub adapter, fixed-shape CLI and CI workflows, and 047-aligned platform contributions.

## Authority and scope

Authority order follows `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, and `.work/programmes/work-management/target-spec.md`.

The repository remains authoritative for specifications and implementation evidence. GitHub remains the initial operational backend. This change does not add a database, a generic GraphQL surface, a fourth hard rule, or permanent deletion.

## Design decisions

- Backend topology is a configurable mix of shared portfolio and per-project bindings.
- The existing pinned official GitHub MCP provider remains the provider boundary.
- Remote mutations require explicit preview/apply selection and idempotency keys.
- Built-in GitHub workflows are represented as desired capabilities; unsupported provisioning remains explicit rather than emulated.
- Project schema repair requires explicit apply mode but no new approval-record type.
- Evidence persistence is repository-local beneath `.work/reviews/<review-id>/` and uses atomic replace with conflict detection.

## Requirements

- **REQ-P5-001 — Settings:** Strict versioned JSON and schema define managed projects, backend bindings, feature modes, automation modes, and gate modes.
- **REQ-P5-002 — Evidence store:** Review evidence is written atomically, validated against the P4 manifest, conflict-aware, bounded, and never permanently deleted.
- **REQ-P5-003 — Reconciliation:** Desired and observed records produce deterministic create, update, no-op, conflict, unsupported, and inaccessible outcomes.
- **REQ-P5-004 — Portfolio status:** Status reports aggregate configured projects while preserving project identity, truncation, provider failures, blockers, risks, documentation state, and traceability gaps.
- **REQ-P5-005 — GitHub adapter:** GitHub identifiers, capability detection, pagination, optimistic concurrency, idempotency, provider errors, and normalized conversion remain inside the provider boundary.
- **REQ-P5-006 — Service:** A provider-neutral facade coordinates capture, selection, reconciliation, review persistence, traceability checks, and status without importing FastMCP or GitHub layouts.
- **REQ-P5-007 — CLI:** `scripts/project-workflow.ps1` delegates to fixed-shape Python commands with bounded JSON, structured exit codes, and dry-run default for mutation.
- **REQ-P5-008 — CI:** A reusable workflow validates settings, evidence, traceability, and programme drift at the exact revision without claiming unavailable server-side enforcement.
- **REQ-P5-009 — Workflows:** Task-level workflow descriptors and bounded operations use normalized services and 047 platform composition.
- **REQ-P5-010 — Isolation:** Provider or work-management failure does not disable unrelated platform capabilities and is never reported as an HR violation.
- **REQ-P5-011 — Documentation:** Programme authority, README, operations, platform concept, and current implementation statements reconcile with the delivered boundary.
- **REQ-P5-012 — Verification:** Focused tests, architecture checks, full repository verification, GitHub capability evidence, exact-head review, merge, post-merge reconciliation, and cleanup are recorded.

## Acceptance scenarios

1. Repeated evidence persistence with identical content is idempotent; conflicting content returns a conflict without overwrite.
2. Reconciliation never overwrites a newer observed record and reports per-record outcomes.
3. Two configured projects produce attributable per-project and portfolio summaries.
4. Missing GitHub capabilities disable only affected workflows and disclose the limitation.
5. CLI mutation commands remain previews unless apply mode and an idempotency key are supplied.
6. CI output identifies the exact commit and exposes advisory versus required gate results.
7. Platform registration exposes bounded task-level operations and no delete or generic GraphQL operation.
8. Full verification passes on the exact reviewed head, and post-merge documentation reconciliation completes before final closeout.

## Risks and recovery

- **Concurrent remote edits:** use observed revision/update tokens and return conflict results. Recovery is operator review and a fresh preview.
- **Partial provider capability:** capability-detect and mark individual actions unsupported. Recovery is disabling only that feature or commissioning a compatible provider release.
- **Evidence interruption:** write temporary files in the target directory and atomically replace only after validation. Recovery uses the intact prior file and retained temporary evidence.
- **Schema drift:** preview normalized desired-versus-observed differences before apply. Recovery is repeatable reconciliation from versioned settings.
- **Automation overreach:** default mutations to preview and require explicit apply plus idempotency. Recovery uses GitHub history and repository evidence; no delete operation is provided.

## Out of scope

- Organization-only issue types or issue fields.
- Paid branch protection or ruleset enablement.
- Arbitrary GraphQL or REST passthrough.
- A second external database or custom project-management UI.
- Automatic resumption of holds.
- Permanent deletion or destructive migration.
- P6 stronger enforcement and organization-level enhancements.
