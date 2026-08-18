# Implementation Plan: MCP Authority and Platform Reliability

## Outcome

Deliver one umbrella remediation programme containing seven strictly sequential governed child changes. Each child slice MUST be merged, reconciled, and present on verified local `main` before the next child slice is created.

Every MCP-impacting implementation decision MUST use the installed FastMCP 3.x line and the matching normative MCP `2025-11-25` schema/specification authority. MCP `2026-07-28`, FastMCP 4.x migration/design material, drafts, and later protocol primitives are excluded from current implementation authority unless a separate FastMCP 4.x migration change is explicitly approved.

## Planning constraints

- Umbrella record: `181-mcp-authority-platform-reliability`.
- Documentation level: Complex, because this programme establishes governing protocol-source controls and modifies architecture/public contracts.
- The umbrella record owns programme requirements and traceability only.
- Each implementation slice owns its own governed child change ID, branch, worktree, scope claims, exact upstream SHA/tree, PR, verification, review, merge, landing receipt, and cleanup evidence.
- Child slices are created only from the exact merged `main` produced by the previous slice.
- No later slice may contain implementation work while an earlier slice is still open, unmerged, unreconciled, or not reflected in clean registered local `main`.
- Preserve compatibility unless official MCP authority proves current KIS behavior is invalid.

## Slice 1 — MCP authority gate, canonical source, and product execution environment

1. Map every MCP-facing server/client/protocol surface and every governed change entry point that can create, validate, review, or verify MCP-impacting work.
2. Resolve FastMCP implementation guidance only from the 3.x line and protocol authority only from MCP `2025-11-25`, progressively from the versioned MCP index to applicable normative prose and exact schema types.
3. Define machine-readable `McpProtocolImpact` and `McpAuthorityReceipt` contracts that bind FastMCP major `3` to MCP revision `2025-11-25` and reject newer/draft authority for current work.
4. Expose the pinned `2025-11-25` specification/schema through MCP Resources where appropriate.
5. Advertise concise agent guidance through `InitializeResult.instructions`, pointing clients to the authoritative resources.
6. Add fail-closed validation and canonical verification for missing, stale, mismatched, unversioned, newer-major, or incomplete MCP authority receipts.
7. Add conformance tests proving an MCP-impacting change cannot bypass consultation.
8. Introduce canonical `ResolvedSource` identity shared by discovery, verification, review, completion, and execution.
9. Introduce generic `ProjectExecutionContract -> ResolvedExecutionEnvironment` resolution and separate product-repository execution from KIS's own runtime/tool environment.
10. Commission at least one real repository, including `doc-solution`, only as acceptance evidence; no repository-specific special case is allowed.

Slice 1 exit gate: exact-head tests/reviews pass; PR is merged; local `main` safely aligns to the exact merged head; child change and worktree are reconciled/cleaned.

## Slice 2 — Review orchestration v2

1. Replace fixed NVIDIA/Codex fallback assumptions with a provider-neutral backend pool.
2. Add health, typed failure, cooldown, retry/backoff, and reserved fallback-budget contracts.
3. Reuse issue #335 for deterministic complete semantic batching rather than creating a second batching design.
4. Add deterministic review context manifests carrying bounded relevant unchanged definitions/contracts/tests.
5. Reject or downgrade findings that cannot resolve to supplied evidence.
6. Add positive and negative reviewer calibration fixtures, including the known valid commissioning constructs.
7. Keep manual exact-diff review as final safety fallback only.
8. Do not build new orchestration on deprecated MCP Sampling.

Slice 2 exit gate: full review coverage is proven across review types and batches; failure-domain tests pass; merged/reconciled/clean before Slice 3 starts.

## Slice 3 — Complete Work Management pagination

1. Add a first-class page contract containing items, continuation cursor, and completeness.
2. Add bounded auto-drain for operations requiring authoritative complete inventory.
3. Make truncation explicit and fail closed where incomplete authority would affect selection/readiness/merge decisions.
4. Apply the contract to inventory, current work, next work, readiness, and exact-target lookup.
5. Add multi-page and bound-exhaustion regression tests.

Slice 3 exit gate: authoritative operations prove completeness or return typed incompleteness; merged/reconciled/clean before Slice 4 starts.

## Slice 4 — Durable reviewable PR and authoritative pre-merge readiness

1. Convert PR preparation into durable idempotent stages: `resolve -> verify -> review -> publish -> create_pr`.
2. Persist stage receipts keyed by operation/source/config fingerprints.
3. Give each stage its own bounded deadline and resume from the last proven stage after interruption.
4. Add authoritative Work Management bootstrap/reconcile at the pre-merge boundary.
5. Bind readiness to exact-head verification and review evidence.
6. Fail closed on ambiguous or conflicting human-owned metadata.
7. Preserve the public outcome: an open exact-head reviewable PR; do not solve by simply increasing a composite timeout.

Slice 4 exit gate: interruption/resume and pre-merge readiness tests pass; merged/reconciled/clean before Slice 5 starts.

## Slice 5 — Registered repository and Windows worktree lifecycle

1. Keep low-level remote-tracking refresh semantics stable.
2. Add explicit safe default-branch alignment owned by serialized integration/landing flow.
3. Allow only clean fast-forward advancement; dirty/diverged state returns a typed stop; no force/reset.
4. Ensure long-lived processes inherit neutral KIS-state CWD rather than governed worktree CWD.
5. Ensure short-lived worktree commands are KIS-owned and fully reaped through the existing Windows process-tree/Job Object boundary.
6. Add bounded handle-release retry.
7. Add deterministic lock diagnostics from KIS process metadata first and native Windows best-effort inspection second.
8. Permit automated termination only for positively identified KIS-owned processes; unknown/external holders are reported only.

Slice 5 exit gate: Windows lifecycle regressions pass; registered main alignment is safe; merged/reconciled/clean before Slice 6 starts.

## Slice 6 — Post-merge lifecycle reconciliation

1. Reconcile stale historical change 179 from authoritative merge evidence.
2. Define structured `LandingReceipt` or equivalent machine-owned closeout facts.
3. Add idempotent post-merge reconciliation using exact GitHub merge commit/tree truth.
4. Reconcile machine-owned change status, local-main alignment, branch/worktree cleanup, and documentation closeout without rewriting human review narrative.
5. Integrate the same primitive into issue #325's scheduled reconciler direction as a safety net.
6. Add repeated-run/idempotency and stale-record recovery tests.

Slice 6 exit gate: stale 179 is corrected by the new primitive, not by a one-off bypass; merged/reconciled/clean before Slice 7 starts.

## Slice 7 — Permanent execution and commissioning acceptance matrix

1. Extract a hermetic normal-suite acceptance matrix covering Small/Medium/Large changes.
2. Cover two concurrent exact runs, distinct product execution environments, exact SHA/tree/fingerprint identity, unique run/workspace namespaces, timeout/parent-loss containment, stale-run recovery, and receipt integrity.
3. Add deterministic regression cases for contracts introduced by Slices 1–6.
4. Keep live reviewer/provider and real registered product-repository commissioning in a separate optional/live profile.
5. Mandatory verification MUST NOT depend on live NVIDIA, Codex, GitHub Actions, or an external product repository.
6. Run the full programme acceptance matrix on the exact final Slice 7 head.

Slice 7 exit gate: final exact-head canonical verification and required reviews pass; PR is merged; local `main` aligns and is clean; umbrella programme is reconciled and closed.

## Mandatory sequential landing gate

For every child Slice `N`, KIS MUST complete all of the following before Slice `N+1` may be created:

1. implement only the current slice and required compatibility/regression work;
2. run focused verification and all required risk-trigger reviews on the exact current head;
3. prepare and review the exact-head pull request;
4. satisfy authoritative Work Management merge readiness;
5. merge only the approved exact head;
6. refresh remote truth and safely align registered local `main` to the exact merged GitHub head;
7. reconcile landing receipt, child change status, remote branch, and worktree cleanup;
8. verify repository cleanliness and confirm the next child slice's immutable upstream SHA/tree.

Failure of any item blocks creation or implementation of the next slice.
