# Change Specification: Commissioning Runner Evidence Lifecycle

- **Change ID**: `229-commissioning-runner-evidence-lifecycle`
- **Work item**: `#454`
- **Development level**: Complex
- **Status**: Approved for implementation
- **Risk profile**: architecture boundary, external action, persistent state, public contract

## Outcome and current state

Change 228 already owns deterministic merged-PR observation, exact merge/scope resolution, live-surface classification, and one idempotent commissioning issue per `repository + merge SHA + surface` obligation. It intentionally does not execute live proof or project source live-verification evidence.

Change 229 adds the explicit execution lifecycle for one generated obligation. It must preserve source repository delivery as already landed, use existing Work Management authority for commissioning-task state, exercise a real exposed KIS path, retain bounded durable evidence, and project source live-verification state independently from source `Verification`.

## Authority and scope

Authoritative inputs are `#419`, `#454`, the approved Change 228 commissioning contract, `AGENTS.md`, `docs/COORDINATOR-MODULE-PRODUCT-SPEC.md`, the canonical Work contracts, and `settings/post-merge-commissioning.settings.json`.

The runner is an explicit supervised operation. The existing `kis-op` scheduled observer remains discovery/intake authority only. Housekeeping authority is unchanged.

No new generic task system, mutation-authority plane, GitHub credential authority, or timer-driven commissioning execution is introduced.

## Requirements and invariants

- **R1 — Deterministic intake identity.** The runner accepts only an existing commissioning issue whose body exactly parses the Change 228 contract. It re-resolves the source PR, merge SHA, schema-v4 change scope, classification, surface, and obligation key before any mutation. Malformed, stale, duplicated, or contradictory identity fails closed.
- **R2 — Existing Work authority.** Before execution, the exact commissioning issue must be observable as `Active` and claimed by the supplied execution owner through canonical Work Management. Board evidence is read through `project_management_board_data`; the runner does not create or infer a parallel claim.
- **R3 — Frozen execution contract.** The exact repository, source issue, source PR, merge SHA, change ID, surface ID, obligation key, runtime instance, refresh rule, probe profile, expected invariant, evidence target, and success criterion are frozen for an attempt. A retry revalidates the same obligation identity.
- **R4 — Machine-readable refresh and probe policy.** Each configured surface declares a strict `probe_id` in the commissioning settings in addition to the existing machine-readable `refresh_rule`. Supported probe IDs map to bounded, read-only exposed KIS operations with deterministic response predicates. No prose, LLM judgment, shell string, or arbitrary operation name is executable authority.
- **R5 — Safe runtime-generation gate.** `refresh_rule=none` does not require a generation refresh. `refresh` or `restart` requires the current configured runtime generation to contain the frozen merge. Runtime source revision comes from the real exposed health path and ancestry is checked read-only against the local governed repository. A stale generation produces `Blocked/runtime_refresh_required` before the live probe.
- **R6 — No self-termination.** A runner executing inside `kis-op` must never kill or restart its own hosting process. When a restart is required, it records Blocked evidence and stops. The existing supervised instance launcher performs the restart outside the request; an explicit retry then resumes the same obligation.
- **R7 — Real live path.** The proof step invokes the configured probe profile through the actual mounted KIS/FastMCP tool path and evaluates only its deterministic bounded predicate. Repository tests, direct Python calls, or synthetic unit fixtures cannot produce `Passed` evidence.
- **R8 — Durable execution evidence.** Per-obligation state and receipts live under the existing commissioning state namespace. Receipts contain bounded identities, attempt/phase, runtime source revision, probe ID, response fingerprint/selected assertion evidence, result, and compact error codes; they never retain free-form runtime logs, credentials, prompts, or full provider bodies.
- **R9 — Idempotent resume/retry.** A completed `Passed` obligation replays without re-running the probe or duplicating mutations. Interrupted phases resume from durable state. `Failed` or `Blocked` is stable until an explicit `retry=true`, which creates the next attempt after full identity revalidation. All Work/source mutations use deterministic idempotency keys.
- **R10 — Source verification separation.** Commissioning projection may write only `Live Verification`, `Commissioning Key`, and `Live Verification Evidence`. It must never include, clear, or rewrite source `Verification`, delivery/merge evidence, or source issue state.
- **R11 — Multi-obligation source aggregation.** Per-surface commissioning keys remain the Change 228 issue identities. Source projection is recomputed from the complete classifier obligation set for the frozen merge so one surface cannot overwrite another. With one obligation, source `Commissioning Key` is that exact key. With multiple obligations, it is `commission:<normalized-repository>:<merge-sha>:set-<digest24>`, where `digest24` is the first 24 hexadecimal characters of SHA-256 over the sorted newline-delimited obligation keys.
- **R12 — Aggregate live state.** Source `Live Verification` is `Passed` only when every required obligation has passed; `Failed` if any obligation failed; otherwise `Blocked` if any obligation is blocked; otherwise `Pending`. A no-obligation classification remains `Not Required` and is not produced by the runner. The aggregate evidence receipt records the ordered per-obligation key/state/receipt references that produced the source value.
- **R13 — Commissioning task lifecycle.** A blocked proof transitions the commissioning Work item to `Blocked`; a failed proof leaves it open/active for explicit retry; a passed proof completes the commissioning Work item through `project_management_complete_work` and closes the generated GitHub issue only after canonical Work completion succeeds. Commissioning operational tasks have no repository-documentation obligation of their own.
- **R14 — Bounded source projection.** The source projection uses canonical `project_management_reconcile` against fresh inventory/revision evidence. It projects an aggregate key and a compact `commissioning-evidence:<sha256>` receipt reference. Source state may already be `Done`; commissioning evidence does not reopen it.
- **R15 — Public runtime surface.** Add one explicit runner operation and one read-only execution-evidence operation to the commissioning capability contribution. The runner operation is externally mutating, discoverable, and approval-required; diagnostic observer tools remain read-only.
- **R16 — Observer compatibility.** Change 228 checkpoint, overlap, intake idempotency, first-activation no-backfill behavior, issue body contract, and scheduled observer authority remain compatible. #455 remains the only historical backfill owner.
- **R17 — Source classification projection.** After exact classification/intake, the observer initializes source live state through canonical reconciliation: required obligations -> `Pending` plus the deterministic source key and sorted commissioning-issue linkage; no obligations -> `Not Required` with no commissioning key; ambiguous high-risk classification -> `Blocked` with exact merge/classification evidence and no invented obligation key. This projection also never writes source `Verification`.

## Architecture and data flow

```text
generated commissioning issue
  -> strict issue parser + exact Change 228 evidence re-resolution
  -> exact Work board/claim re-read
  -> durable execution attempt (frozen obligation)
  -> refresh-rule/runtime-generation gate
  -> configured read-only live probe through real KIS tool path
  -> per-obligation receipt
  -> recompute source aggregate from all obligation receipts
  -> idempotent Work source projection
  -> Blocked / retryable Failed / successful commissioning closeout
```

The commissioning settings remain the machine-readable surface-policy owner. `probe_id` selects one code-owned, closed probe profile; profile implementations contain the exact tool invocation and bounded predicate so configuration cannot become arbitrary tool execution.

## Initial probe profiles

| `probe_id` | Real exposed operation | Deterministic pass condition |
|---|---|---|
| `coordinator-work-board` | `project_management_board_data` | Complete authoritative board read returns exactly the executing commissioning card for the frozen issue/owner query. |
| `gateway-health` | `kis_health` | `ready=true`, runtime instance matches the obligation runtime, and runtime source revision is a valid governed revision containing the frozen merge. |
| `housekeeping-status` | `kis_housekeeping_status` | Current instance matches the configured host, service is active, and scheduled targets report active scheduler ownership. |
| `provider-status` | `kis_provider_status` | Platform health is `ready` with zero unavailable providers; the bounded provider status call itself runs through the mounted runtime. |
| `post-merge-observer-status` | `kis_post_merge_commissioning_status` | Current instance is the configured host, observer is active, target checkpoint is ready/fresh, and the target scheduler is active. |
| `work-management-contract` | `project_management_contract` | Canonical Work contract returns schema version 1 and retains distinct source/live verification domains. |

All probe calls are dispatched through `execute_read_action`; generic-dispatch recursion, mutation-capable operations, and unknown probe IDs are rejected. The runner does not accept caller-supplied operation names or assertion expressions.

## Source aggregation contract

The source projection receipt is authoritative for aggregation, not the Project text fields themselves. It contains the frozen merge identity, the full classifier obligation-key set, and for each key either its latest execution receipt or `pending`. The Project fields are a compact projection of that receipt.

Aggregate precedence is deterministic: `Failed` > `Blocked` > `Pending` > `Passed`. `Passed` requires all obligations to be passed. A later successful explicit retry replaces the latest state for that obligation and causes a new aggregate receipt/projection; historical receipts remain immutable.

The canonical Work item-semantics definition for `Commissioning Key` is updated only enough to permit the singular key for one obligation and the deterministic `set-<digest24>` source key for a multi-obligation merge. Provider field type and live-verification vocabulary do not change.

## Trust, security, and failure boundaries

- Live probes are read-only. The only external mutations are canonical Work/source projection, Work lifecycle transition/completion, and successful commissioning-issue closure.
- The runner never accepts raw commands, URLs, credentials, arbitrary tool names, arbitrary JSON predicates, or free-form executable procedures.
- External mutation begins only after identity, current claim, runtime-generation, and probe-contract validation.
- Provider/network access still runs through existing KIS operation contracts and middleware; no HR-001/HR-002/HR-003 exception is added.
- Failed/blocked evidence is not interpreted as repository delivery failure and cannot reopen the source issue.
- Successful closeout orders mutations as: persist proof -> project source aggregate -> canonical Work completion -> GitHub commissioning issue close. Replay may safely repeat the latter idempotent steps.

## Acceptance and release evidence

1. Malformed/stale/contradictory commissioning issue identity is rejected before mutation.
2. The exact merge SHA and obligation key remain frozen across execution, interruption, retry, and resume.
3. Tests cover every probe profile plus unknown/mutation-capable probe rejection.
4. Tests cover refresh `none`, current-generation `restart`, stale-generation Blocked, supervised restart, explicit retry, interrupted resume, replay of Passed, Failed, and Blocked.
5. Tests prove source `Verification` is byte-for-byte absent from commissioning reconciliation writes.
6. Tests cover one- and multi-obligation source aggregation and failure/block/pending/pass precedence.
7. Success retains a bounded per-obligation receipt and aggregate receipt, completes Work, then closes only the commissioning issue.
8. Failed and Blocked commissioning work remains open and actionable without changing source delivery state.
9. Focused tests, Ruff, scope check, required specialist reviews, and exact-head canonical GitHub Actions pass.
10. After merge, refreshed `kis-op` must let the Change 228 observer discover Change 229 independently, create/reuse the exact `post-merge-observer` commissioning issue, and the newly landed runner must consume that issue through the real runtime. This live smoke is also the remaining Change 228/#453 release proof.

## Rollback and recovery

Rollback is repository revert plus supervised `kis-op` refresh. Existing Change 228 observer checkpoints/intake remain valid because their persisted schemas and issue contract are preserved.

Execution and aggregate receipts are append-only evidence. A failed deployment may leave an open commissioning issue and `Pending`/`Failed`/`Blocked` source projection; after corrected code/runtime, explicit retry revalidates identity and advances from the durable obligation state. No recovery path deletes evidence or rewrites source repository verification.

## Explicit exclusions

- Historical commissioning/backfill (#455).
- Changes to housekeeping scheduled apply authority.
- A generic runtime restart service or self-restart from an MCP request.
- Arbitrary user-defined probe code or shell execution.
- Redesign of coordinator reservations/work packets or source delivery verification.
- New Project fields or a new commissioning-required boolean.

## Approval gate

Implementation must not begin until this specification and the matching implementation plan are explicitly approved under the repository Complex development gate.