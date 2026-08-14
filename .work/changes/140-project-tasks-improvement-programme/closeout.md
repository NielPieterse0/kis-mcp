# Closeout: Project Tasks Improvement Programme

## Status

Repository implementation and pre-merge review are complete. Final exact-head Canonical Verification and merge remain pending. Live KIS runtime commissioning and native Project/sub-issue projection remain separate post-merge evidence gates because this ChatGPT host cannot invoke `kis-dev` / `kis-op` or Projects-v2/sub-issue mutations.

## Delivery evidence

- Programme issue: #215
- Slice issues: #216, #217, #218, #219
- Governed change: `140-project-tasks-improvement-programme`
- Branch: `change/140-project-tasks-improvement-programme`
- Pull request: #221
- Initial governed base: `194b693e916bc6cbef2f24eb8912eb49cf6fab85`
- Recovery-capsule change 136 landed independently through PR #222 at main `1ee03bba4b7979d77b3df0e365d1638959eb3149`.
- Exact file-intersection check between PR #221 and PR #222 implementation surfaces was empty.
- Change 140 was reconciled with landed change 136 through two-parent integration commit `55ade2511eff36cfa94e74a923bcb585d8cf5a4f`, preserving both histories.

## Delivered behavior

### #216 — Runtime generation identity

- Remote readiness validates current lifecycle, instance, endpoint, listener PID, serving Git/config generation, bounded run identity, canonical startup-evidence path, startup health, matching endpoint/PID, and policy fingerprint.
- The serving process captures source/config generation at import time and rejects stale checkout/config evidence.
- Startup evidence is accepted only from canonical `startup-state-<run_id>.json` in the selected runtime directory; arbitrary pointer redirection is rejected.
- Typed stale/not-ready evidence is surfaced without upgrading external-tunnel readiness.
- Focused tests cover matching ready state, stale/mismatched lifecycle/instance/endpoint/PID/source/config generation, missing/mismatched startup evidence, invalid run identity, and noncanonical evidence paths.

### #217 — Current/resume workflow

- `project_management_current_work` is read-only and resumes an already claimed Active item without reacquiring or mutating its claim.
- None, exactly-one, multiple, and truncated-inventory outcomes are deterministic; multiple/truncated cases never guess a current item.
- Exactly one current item returns normalized source/change/owner context and bounded next actions.

### #218 — Normalized Work board / Control Center

- `project_management_board_data` provides one active-first normalized projection over authoritative Project inventory with state counts, cards, filters, grouping, completeness/truncation, provenance, and next-eligible evidence.
- The board reads the existing readiness/queue fields and uses the existing `select_next_project_item` semantics rather than creating a parallel queue.
- A process-local disposable `WorkBoardProjectionBridge` publishes only the latest derived board read.
- Control Center provider composition injects that exact projection into `ControlCenterSnapshot.work_board`; Control Center does not query GitHub independently, reinterpret Project fields, or persist a mirror.
- Until an authoritative board read occurs, Control Center explicitly reports the Work board as unavailable.

### #219 — Contract hardening

- New current-work/board operations use an additive observation/provenance/result/next-action envelope.
- Typed Work Management failures distinguish provider unavailable, uncommissioned project, incomplete inventory, conflict, invalid transition, not found, invalid request, and internal failure classes.
- FastMCP annotations distinguish provider-backed reads, local reads, provider mutations, and local review-evidence persistence.
- Existing successful legacy Project Management payloads and explicit `apply`/idempotency semantics remain backward compatible.
- `project_management_contract` documents the complete operation/effect map, result envelope, error vocabulary, and mutation rule.

## Documentation

- `docs/PROJECT-TASKS-IMPROVEMENT.md` records the additive programme contracts, authority boundaries, operational semantics, and post-merge commissioning requirements.
- Fresh recovery-capsule authority material landed in `SPEC.md` and `docs/OPERATIONS.md` via change 136 and was preserved exactly during the change-140 integration rather than overwritten or duplicated.
- The programme document explicitly complements those existing authority documents and does not introduce a second Work authority.

## Review evidence

Required specialist reviews are recorded beneath this change:

- `reviews/code-quality.md` — PASS after corrections.
- `reviews/architecture.md` — PASS after corrections.
- `reviews/api-contracts.md` — PASS after corrections.

Blocking findings corrected during review included governance-schema defects, readiness-field completeness, package-boundary allowlisting, hidden Control Center dependency injection, external-vs-local MCP effect annotations, complete operation mapping, and canonical startup-evidence path validation.

## Verification

Canonical verification history provided iterative fail-closed evidence rather than being treated as pass-by-absence:

- early runs rejected invalid change-governance metadata before tests;
- run #105 reached the full repository suite and found only the intentional Work Management architecture allowlist delta;
- integrated run #117 against current main found only one invalid-run test-fixture defect; the runtime implementation itself had reached that validation path correctly;
- the fixture was corrected to publish the invalid `run_id` without first trying to create an invalid filesystem path.

A final Canonical Verification run on the resulting documentation/closeout head is mandatory before merge. The PR must not merge from an earlier successful implementation head.

## Commissioning and residual gates

Live KIS commissioning is **not claimed** in this host. Post-merge commissioning still requires a KIS-enabled surface to prove, on the landed source revision:

1. restart/initialize `kis-dev` and `kis-op` as required;
2. runtime evidence reports `ready` for the new source/config generation;
3. `project_management_current_work`, `project_management_board_data`, and `project_management_contract` are discoverable with the documented read/effect semantics;
4. a bounded authoritative board read publishes the same normalized payload consumed by Control Center;
5. stale generation evidence cannot report ready.

Native GitHub Project #1 membership and native sub-issue relationships for #215–#219 also remain pending because the available GitHub connector exposes issue CRUD but no Projects-v2 item or native sub-issue mutation.

These residual commissioning/projection gates do not justify bypassing repository verification or inventing completion evidence. Child/parent issue closure must be reconciled to the actual post-merge evidence rather than closed optimistically.
