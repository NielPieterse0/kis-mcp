# Commissioning Runner Evidence Lifecycle Implementation Plan

> **For agentic workers:** Execute only after the Complex specification and this plan are explicitly approved. Keep `scope.json` current and use tests before behavior changes.

**Goal:** Implement #454 without changing source delivery authority: exact generated commissioning work is claimed through Work, verified against the real runtime, persisted idempotently, aggregated across surfaces, and projected only into the canonical live-verification fields.

**Architecture:** Extend the existing Change 228 commissioning module rather than creating a second service. The scheduled observer keeps discovery/intake ownership; an explicit approval-required runner uses the same strict settings/evidence/state boundary. Surface settings add a closed `probe_id`. Runner probe execution is read-only through `execute_read_action`; external mutations use existing Work/GitHub operations with deterministic idempotency.

**Tech stack:** Python 3.13 locked runtime, FastMCP, existing KIS capability dispatch, GitHub MCP provider, canonical Work Management, pytest, Ruff, change governance, GitHub Actions.

## Traceability matrix

| Task | Requirements | Inputs / outputs | Dependencies | Test-first evidence | Review gate | Verification evidence | Recovery |
|---|---|---|---|---|---|---|---|
| T1 | R4, R7, R16 | Settings -> strict probe profiles | Change 228 settings | Invalid/missing/unknown probe red tests | API/contracts | Focused settings tests | Revert settings/parser together |
| T2 | R1, R3 | Commissioning issue -> frozen obligation | Existing resolver/classifier | Malformed/stale/contradictory identity red tests | Architecture/API | Identity suite | No mutation before success |
| T3 | R8, R9 | Obligation -> durable attempt/receipt | Existing state root | Replay/interruption/retry red tests | Architecture | State suite | Append-only evidence; retry generation |
| T4 | R5-R7 | Frozen attempt -> live probe result | T1-T3 | stale/current/none refresh and probe red tests | Security/architecture | Probe/runtime suite | Block; supervised refresh; retry |
| T5 | R10-R12, R14, R17 | Classifier/receipts -> source projection | Work reconcile | pending/not-required/aggregate red tests | API/contracts | Projection suite | Reconcile idempotently from receipts |
| T6 | R2, R13 | Commissioning Work item -> blocked/open/done | Work lifecycle | claim mismatch/fail/block/pass red tests | Architecture | Lifecycle suite | Leave issue open unless pass closeout |
| T7 | R15 | Service -> exposed runner/evidence tools | T1-T6 | tool/capability metadata red tests | API/security | Gateway/discovery tests | Remove exposure; receipts remain readable |
| T8 | R16 | Existing observer -> source classification initialization | T5 | observer regression + source projection red tests | Architecture | Observer suite | Checkpoint/intake schema unchanged |
| T9 | R1-R17 | Docs/contracts -> current behavior | T1-T8 | canonical contract expectation updates | Documentation | docs/contract checks | Revert coupled documentation |
| T10 | R1-R17 | Exact change -> reviewable PR/live smoke | T1-T9 | affected tests then exact-head CI | All required | scope/Ruff/focused + GitHub Actions + live smoke | Revert/refresh; retain failed evidence |

## T1 — Make probe policy executable but closed

**Modify:** `settings/post-merge-commissioning.settings.json`, `src/kis_mcp/commissioning/settings.py`  
**Test:** `tests/post_merge_commissioning/test_policy.py`

1. Add exactly one required `probe_id` to each surface and bump the commissioning settings schema only if the persisted/config contract requires it; parser and checked-in settings change atomically.
2. Define the six approved probe IDs from the specification as a closed vocabulary. Reject missing, duplicate/invalid, or unsupported values.
3. Keep `verification_procedure`, `expected_invariant`, and terminal criterion informative; they cannot become executable expressions.
4. Add red tests before parser/settings changes, then focused green tests.

## T2 — Parse and freeze one generated obligation

**Modify:** `src/kis_mcp/commissioning/models.py`, `src/kis_mcp/commissioning/intake.py`, new focused runner/identity module under `src/kis_mcp/commissioning/`  
**Test:** new/updated `tests/post_merge_commissioning/test_runner_identity.py`

1. Add a strict parser for the exact generated issue title/body contract; require each marker exactly once and reject extra/contradictory identity markers.
2. Re-read the issue from GitHub, re-run `MergedChangeResolver`, re-run classification, and require exactly one matching obligation for the issue key/surface.
3. Freeze a typed execution contract including probe ID and all Change 228 obligation facts.
4. Prove no Work/source mutation call occurs on every identity rejection path.

## T3 — Add durable execution and aggregation evidence

**Modify:** `src/kis_mcp/commissioning_runtime/state.py`, commissioning models/state helpers  
**Test:** `tests/post_merge_commissioning/test_state.py`, new execution-state tests

1. Add deterministic execution-state identity keyed by commissioning key, with attempt number, phase, frozen contract fingerprint, latest terminal result, and receipt references.
2. Persist immutable per-attempt receipts and immutable source aggregate receipts under the existing commissioning namespace with bounded retention and canonical JSON hashing.
3. Terminal `Passed` replay returns existing evidence. `Failed`/`Blocked` replay without retry returns existing evidence. `retry=true` increments attempt only after exact identity revalidation.
4. Treat in-flight read-only probe interruption as resumable; never duplicate Work/source mutations because mutation keys are phase/key/attempt deterministic.

## T4 — Gate runtime generation and execute the real probe

**Modify:** `src/kis_mcp/commissioning_runtime/invoker.py`, runner service/probe module  
**Test:** `tests/post_merge_commissioning/test_invoker.py`, new `test_probes.py`, runner service tests

1. Add bounded `read` and `change` dispatch helpers that call existing `execute_read_action` / `execute_change_action`; keep external GitHub calls on `execute_external_action`.
2. Read `kis_health` from the actual obligation runtime. Validate runtime identity/source revision and use read-only `git merge-base --is-ancestor <merge> <runtime-source>` against the governed local repository for refresh/restart rules.
3. For stale generation, persist `Blocked/runtime_refresh_required`, skip the probe, and return a supervised restart action; never spawn/stop the hosting runtime.
4. Implement the six code-owned probe profiles. Each invokes only its fixed read operation and emits selected bounded assertion evidence plus a response fingerprint.
5. Unknown profile, generic-dispatch recursion, malformed response, or failed predicate produces deterministic Failed/Blocked evidence as specified by the error class.

## T5 — Project classification and aggregate source live state

**Modify:** commissioning projection helper; `settings/work-management/contracts/work-item-semantics.json`  
**Test:** projection tests plus `tests/work_management/test_canonical_contracts.py`

1. Use a fresh complete authoritative Work Project read to locate exactly the source item and its current authority revision; prefer bounded exact `project_management_board_data` query evidence so the projection cannot depend on a truncated full-project inventory. Never synthesize observed revision.
2. Extend observer results: required -> Pending + deterministic source key + sorted issue linkage; not required -> Not Required; ambiguous -> Blocked. Do not include `Verification` in supported/desired fields.
3. Recompute the required obligation set from the exact frozen merge before every runner projection; load latest per-obligation receipts and create an immutable aggregate receipt.
4. Apply the specification precedence and one-vs-set Commissioning Key rule; project only the three live fields through `project_management_reconcile` with deterministic idempotency.

## T6 — Reuse Work lifecycle authority for commissioning tasks

**Modify:** runner lifecycle helper under `src/kis_mcp/commissioning_runtime/`  
**Test:** new `tests/post_merge_commissioning/test_runner_lifecycle.py`

1. Require the commissioning issue to be `Active` and claimed by the requested execution owner before probe execution.
2. On Blocked, transition the commissioning Work item through canonical Work transition with exact blocker metadata; leave the source issue open.
3. On Failed, retain the commissioning item as visible Active work and persist retry evidence; do not close or reopen source delivery.
4. On Passed, call canonical Work completion first, then close the generated GitHub issue only after Work completion reports success.
5. Use stable idempotency keys for every Work and GitHub mutation and prove replay cannot duplicate lifecycle transitions.

## T7 — Expose explicit commissioning runner/evidence operations

**Modify:** `src/kis_mcp/commissioning_runtime/capability.py`, `src/kis_mcp/commissioning_runtime/platform.py`  
**Test:** capability/discovery/gateway tests

1. Register `kis_post_merge_commissioning_run` as discoverable, approval-required, externally mutating.
2. Register a bounded read-only execution-evidence lookup operation.
3. Preserve the existing observer status/receipt contracts and capability IDs.
4. Verify exposure metadata and runtime tool registration through existing capability tests.
## T8 — Preserve observer semantics while initializing live state

**Modify:** `src/kis_mcp/commissioning_runtime/processor.py` and projection helper  
**Test:** observer processor/runtime regression tests

1. After deterministic classification/intake, initialize source live-verification fields from classification without changing observer checkpoint behavior.
2. Required obligations project Pending plus deterministic aggregate key and sorted issue linkage.
3. No obligation projects Not Required; ambiguous high-risk classification projects Blocked with compact classification evidence.
4. Preserve first-activation no-backfill, overlap, candidate ordering, budgets, and intake idempotency.

## T9 — Reconcile canonical documentation and contracts

**Modify:** `SPEC.md`, `docs/OPERATIONS.md`, `docs/operations/post-merge-commissioning.md`, canonical Work semantics only where required  
**Test:** canonical contract/documentation checks

1. Document the observer/runner authority split, explicit retry/restart boundary, per-surface receipts, and aggregate source projection.
2. Keep source Verification explicitly separate and preserve #455 ownership of historical backfill.
3. Update only executable contract text required to make aggregation/projection semantics machine-readable.
4. Verify documentation and implementation terminology match exactly.
## T10 — Review, verify, land, and commission the runner

**Modify:** closeout/task evidence only after implementation  
**Evidence:** focused tests, scope check, exact-head Actions, live commissioning smoke

1. Run focused affected tests, Ruff on changed Python, `git diff --check`, and `scripts/change-workflow.ps1 check`.
2. Run required architecture, safety/security, API-contract, code-quality, and test-quality review over the exact implementation diff; fix blocking findings and re-run affected evidence.
3. Publish the exact source commit, create the registered PR, and require provider-native Canonical Verification success on that exact PR head plus Work merge-readiness.
4. Merge only the approved head, refresh local `main`, and complete post-merge documentation reconciliation.
5. Let the already-running Change 228 observer independently detect this fresh post-checkpoint runtime-affecting merge and create/reuse exactly one `post-merge-observer` commissioning issue for Change 229.
6. Refresh `kis-op` through the supervised launcher because this change requires restart, claim the generated commissioning issue through Work, run the newly landed explicit runner, and prove exact-merge live evidence reaches Passed without changing source Verification.
7. Record source PR, merge SHA, observer receipt, commissioning issue/key, runner evidence receipt, source live-field readback, and runtime source revision.
8. Close #453 only after its observer acceptance is satisfied; complete #454 only after runner live acceptance and post-merge reconciliation; then clean Change 229 from synced primary `main` while retaining the remote review branch.

## Approval and stop conditions

- Specification approval: user instruction on 2026-08-21 to continue and stop only when absolutely needed, issued after the Complex approval gate was explicitly reported.
- Plan approval: same instruction applies to this finalized plan; implementation may proceed without another conversational checkpoint.
- Stop only for a repository/governance authority conflict, destructive action requiring consent, unresolved material product/risk choice, unavailable required credential/runtime authority, or a verification/review failure that cannot be corrected within the approved scope.
