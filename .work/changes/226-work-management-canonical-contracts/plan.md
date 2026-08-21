# Work Management Canonical Contracts Implementation Plan

> **Execution gate:** Approved by the operator on 2026-08-21. Implementation may proceed only within the approved specification and this plan.

**Goal:** Implement the approved #430 Work-specific canonical semantic contracts, eliminate duplicate normative authority, preserve current selection behavior, reconcile obsolete automation settings, and expose canonical semantics through the existing MCP contract tool.

**Development level:** Complex.

**Architecture:** Add three strict Work-specific JSON authorities and one normalized Work contract loader/model. Existing command-plane settings and GitHub Project schema remain downstream projections with exact conformance checks. Consolidate duplicated lifecycle/selection consumers onto the canonical model. Keep provider mutation and live commissioning outside this implementation lane.

**Tech stack:** Python 3.11+, stdlib JSON/dataclasses/enums, checked-in strict JSON settings/contracts, FastMCP existing tool registration, pytest, PowerShell change workflow, GitHub Actions exact-head verification.

## Global constraints

- Stay inside `scope.json`; expand scope only through governed change metadata if discovery requires it.
- Preserve current approved Work behavior unless the specification explicitly changes it.
- Do not implement or encode #444/Change 223 selection tiers.
- Do not invent unresolved product semantics; surface them as approval blockers.
- Do not create a generic MRD framework or reusable schema engine.
- Do not mutate the live GitHub Project directly during implementation.
- Add failing focused tests before each behavior/configuration change.
- Use local focused checks during development; canonical full repository verification belongs to the exact PR head unless separately required.

## Pre-implementation gate

- [x] Human approves `spec.md`.
- [x] Human approves this `plan.md`.
- [x] Re-read #430 correction authority and current `main` before the first implementation edit.
- [x] Confirm Change 226 remains the active governed lane and no new scope overlap exists.
### Task 1 — Canonical contract model and semantic inventory

**Requirements:** REQ-001, REQ-002, REQ-003, REQ-010

**Planned files:**
- Create: `settings/work-management/contracts/work-item-semantics.json`
- Create: `settings/work-management/contracts/work-lifecycle-operations.json`
- Create: `settings/work-management/contracts/work-selection.json`
- Create or extend: one loader/model under `src/kis_mcp/work_management/`
- Test: `tests/work_management/**`

- [ ] Build a source-to-semantic inventory for every current field, enum/token, authority/direction, applicability rule, lifecycle guard, and selection rule.
- [ ] Classify each semantic as explicit authority, current implemented behavior requiring canonicalization, or unresolved product meaning.
- [ ] Stop and obtain operator authority for any unresolved normative meaning before encoding it.
- [ ] Add strict parser/model tests: exact keys, schema version, uniqueness, referential integrity, invalid rules, and cross-contract consistency.
- [ ] Add the three canonical JSON contracts with complete approved definitions.
- [ ] Implement one immutable loader/model; no provider/FastMCP dependency.
- [ ] Run focused contract/model tests.

### Task 2 — Make command-plane and Python values projections

**Requirements:** REQ-004, REQ-006, REQ-012

**Planned files:** `command-plane.settings.json`, `command_settings.py`, `contracts.py`, `lifecycle.py`, focused tests.

- [ ] Add failing drift tests showing duplicated command-plane/Python values are rejected when they differ from canonical contracts.
- [ ] Derive or exact-validate field authority, state/value sets, transitions, readiness, claims, delivery, and queue settings against canonical owners.
- [ ] Keep only genuine runtime/configuration knobs settings-owned; repeated semantics are projection data.
- [ ] Make lifecycle evaluation consume canonical transition/guard semantics without changing approved behavior.
- [ ] Add compatibility tests for existing valid records/settings and fail-closed tests for stale projections.
- [ ] Run focused command-plane/lifecycle tests.
### Task 3 — Consolidate selection onto one decision contract

**Requirements:** REQ-005, REQ-006

**Planned files:** `selection.py`, `project_commands.py`, adjacent result/contracts code, focused selection/tool tests.

- [ ] Freeze current provider-backed and normalized-domain selection behavior in explicit regression fixtures before refactoring.
- [ ] Add negative fixtures proving no work-class/#444 tier is part of the decision model.
- [ ] Implement one shared canonical evaluator/decision primitive with adapter-specific evidence extraction only where representations differ.
- [ ] Preserve current eligibility, claim, approval/dependency, Priority, Effort, creation-order, and stable-ID behavior exactly where currently applicable.
- [ ] Return deterministic reason/explanation evidence traceable to canonical rule IDs.
- [ ] Differential-test old/current expected decisions against the consolidated implementation.
- [ ] Run focused selection, board, and command tests.

### Task 4 — Reconcile automation settings

**Requirements:** REQ-008, REQ-010, REQ-012

**Planned files:** `github-projects.settings.json`, `contracts/work-management/github-projects.settings.schema.json`, Work settings loader/tests, `tests/project_onboarding/**`, `docs/operations/work-discover.md`.

- [ ] Add failing tests that reject the obsolete `automation` object and stop advertising its keys.
- [ ] Verify each D-006 replacement/disposition against current implementation and historical lineage before removal.
- [ ] If a removed key is proven to represent an approved missing capability, create a bounded follow-up defect and do not implement that capability in Change 226.
- [ ] Remove the generic automation object from accepted settings and update strict loader/schema expectations.
- [ ] Update tests to assert named current mechanisms, not six `false` switches.
- [ ] Reconcile operator text so housekeeping owns scheduling/receipt-apply behavior explicitly.
- [ ] Run focused settings/onboarding/housekeeping-boundary tests.
### Task 5 — Project projection and #419 fields

**Requirements:** REQ-006, REQ-009, REQ-012

**Planned files:** `github-project-schema.json`, `schema.py`, schema/status/commissioning-focused tests.

- [ ] Add projection-conformance tests tying field names/types/options to canonical Work semantics.
- [ ] Add `Live Verification`, `Commissioning Key`, and `Live Verification Evidence` as the final three managed fields with the exact #419 shape.
- [ ] Keep `Verification` and `Live Verification` semantically distinct in contract and projection tests.
- [ ] Validate view field/filter references against canonical fields/options while preserving provider-specific view ownership.
- [ ] Preserve current schema commissioner boundaries: no deletion/recreate path and no direct live mutation in this task.
- [ ] Add drift tests proving live/provider mismatch remains explicit rather than being reported ready.
- [ ] Run focused schema/status/commissioner tests.

### Task 6 — Expose canonical semantics through MCP

**Requirements:** REQ-004, REQ-007

**Planned files:** `src/kis_mcp/workflows/project_management/**`, `tests/workflows/project_management/**`.

- [ ] Add failing contract-tool tests for canonical sections, versions/fingerprints, rule IDs, and existing result/error/operation metadata.
- [ ] Extend `project_management_contract` to aggregate the canonical model without provider reads or mutation.
- [ ] Keep the existing tool name and FastMCP registration contract; do not add a generic contract/MRD tool.
- [ ] Ensure output is deterministic and bounded enough for tool-user consumption.
- [ ] Add failure-path tests for invalid/stale canonical/projection data.
- [ ] Run focused workflow/tool tests.
### Task 7 — Governance-boundary audit and documentation reconciliation

**Requirements:** REQ-010, REQ-011

**Planned files:** `SPEC.md`, change artifacts, and only the scoped operator documentation required by discovered behavior.

- [ ] Record every governance-relevant rule location and its canonical owner/migration disposition.
- [ ] Verify no provider/workflow/prompt/test-only rule remains normative without canonical traceability.
- [ ] Reconcile `SPEC.md` to state the implemented ownership boundary without duplicating enum definitions or decision tables.
- [ ] Record current live schema drift as commissioning evidence only; do not claim live readiness from repository tests.
- [ ] Update `tasks.md` and `closeout.md` with requirement/task/evidence traceability.
- [ ] Run documentation/contract consistency checks applicable to changed files.

### Task 8 — Review, verification, delivery, and commissioning handoff

**Requirements:** REQ-001 through REQ-012

- [ ] Run focused affected suites and `git diff --check`.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check` from the Change 226 worktree.
- [ ] Run required architecture and API-contract reviews from the configured risk triggers; run test-quality review for selection/conformance coverage.
- [ ] Fix blocking findings, rerun affected checks, and re-review changed scope.
- [ ] Commit only the approved implementation and planning evidence on `change/226-work-management-canonical-contracts`.
- [ ] Publish through the governed PR path; canonical repository verification must pass on the exact GitHub head.
- [ ] Merge only after exact-head Work/GitHub readiness evidence permits landing.
- [ ] Perform post-merge documentation/Work reconciliation and safe governed cleanup from clean `main`.
- [ ] Hand live Project schema repair and real-runtime contract verification to #419 using the exact merge SHA and current schema-status evidence.

## Recovery

All canonical/projection changes are version-controlled and reversible by commit. No destructive Project mutation is introduced. Projection validation fails closed on drift, and live schema repair remains the existing idempotent registered-commissioner workflow. A selection regression blocks publication rather than being compensated by new policy.