# Change Specification: Post-Merge Commissioning Intake

- **Change ID**: `228-post-merge-commissioning-intake`
- **Status**: Approved by parent #419 / child #453 authority
- **Development level**: Complex

## Outcome and current state

Implement #453 as a deterministic `kis-op` post-merge observer/classifier/intake. It observes provider-reported merged PRs independently of KIS merge execution, reads durable landed change-governance evidence, deterministically decides whether live verification is required, and creates at most one linked commissioning issue per repository / exact merge SHA / live surface.

Current authority already separates source `Verification` from `Live Verification`, and Change 227 has live-commissioned the three Project fields. The existing housekeeping runtime is preview-only and MUST remain so. Canonical Verification has no post-merge mutation authority and repository Actions credentials are intentionally read-only.

## Requirements and invariants

- **R1 — Observer host:** run only on configured `kis-op` through a dedicated lifecycle service; do not extend housekeeping timer-driven apply authority.
- **R2 — Merge truth:** accept only exact GitHub/provider evidence where the PR read reports `merged=true`; closed-only PRs are not eligible.
- **R3 — Exact merge identity:** resolve the exact merge commit from the default-branch commit stream and require it to identify the same PR; never infer merge SHA from source head.
- **R4 — Durable source linkage:** parse the merged PR body `Change: <change-id>` and `Issue: #N`, then read `.work/changes/<change-id>/scope.json` at the exact merge SHA and require Work identity consistency.
- **R5 — Single policy owner:** classification rules live in one strict machine-readable settings document and are evaluated deterministically from changed paths plus governed risk triggers; no LLM classification authority.
- **R6 — Classification semantics:** documentation-only, test-only, and governance-metadata-only changes with no configured live surface are `not_required`; configured live surfaces yield one or more obligations; configured high-risk triggers with no resolvable surface fail closed as `blocked_ambiguous`.
- **R7 — Stable key:** each obligation key is exactly `commission:<owner/repo>:<merge-sha>:<surface-id>` using normalized lowercase repository identity and SHA.
- **R8 — Duplicate suppression:** before creation, search existing repository issues for the exact key and treat any match as the existing obligation regardless of open/closed state.
- **R9 — Intake contract:** a created commissioning issue must retain source issue, source PR, exact merge SHA, surface ID, verification procedure/invariant, runtime refresh rule, commissioning key, evidence target, and terminal success criterion.
- **R10 — Source delivery preservation:** intake must not reopen, close, or otherwise rewrite source delivery state. Projection of `Live Verification`/evidence onto the source item is reserved for the commissioning lifecycle slice #454.
- **R11 — Replay/backfill compatibility:** the same pure classifier and key derivation must support later bounded backfill #455 without alternate heuristics.
- **R12 — Observability:** persist bounded local observer checkpoints/receipts beneath the KIS state root so restart resumes safely without relying on conversation state.

## Architecture and data flow

1. `CommissioningLifecycleProvider` starts/stops a dedicated observer service with the parent FastMCP lifecycle.
2. The service activates only when the normalized runtime instance is `kis-op`; first activation records a current-time checkpoint and does not backfill historical merges.
3. Later polls list only recent closed PR candidates since the persisted checkpoint overlap window, then re-read each candidate with `github_pull_request_read(get)` and require `merged=true`.
4. For each merged candidate, resolve the merge commit from the registered default-branch commit stream and verify the commit message identifies that PR under the repository's merge-commit-only landing policy.
5. Read changed-file metadata for the exact merge commit, parse `Issue:` / `Change:` markers from the PR body, and load the exact landed change scope through `github_get_file_contents(..., sha=<merge-sha>)`.
6. The pure classifier maps governed paths/risk triggers to zero or more configured live surfaces. It returns `not_required`, concrete obligations, or `blocked_ambiguous`.
7. For each concrete obligation, derive its commissioning key, search all issue states for that key, and create one commissioning issue only when none exists.
8. Persist a bounded observer receipt/checkpoint after the run. Failed candidates remain retryable because no checkpoint may advance past unaccounted provider failures.

## Boundaries and exclusions

- No GitHub Actions write workflow or new repository token/secret.
- No change to housekeeping preview/apply semantics or `kis_housekeeping_apply_receipt`.
- No arbitrary Project schema administration and no direct Project evidence projection in this slice.
- No live capability execution; #454 owns commissioning execution and evidence lifecycle.
- No historical backfill; #455 owns explicit bounded backfill using this same classifier.
- No LLM-generated classification, issue body, key, or success criterion.
- #409 saved-view drift remains unrelated.

## Security, failure, persistence, and recovery

- Provider reads and issue writes stay inside the already authenticated registered KIS GitHub boundary; no credential material is persisted.
- Settings and landed scope are treated as strict data contracts; malformed or identity-mismatched evidence fails closed.
- Local state contains only bounded timestamps, PR/merge/change identities, classifications, issue references, errors, and fingerprints; no prompt text, credentials, provider bodies, or free-form logs.
- Restart recovery replays an overlap window and relies on deterministic keys plus remote duplicate search; deleting local observer state can cause extra reads but not duplicate commissioning work.
- Disable/recovery is configuration/runtime shutdown plus retained remote issues; source delivery remains untouched.

## Acceptance and release evidence

- **A1 / R1-R3:** lifecycle tests prove only `kis-op` activates, first start establishes a non-backfill checkpoint, closed-only PRs are ignored, and exact merge-commit identity is required.
- **A2 / R4:** tests reject missing/malformed PR markers, missing scope, wrong change ID, wrong source issue/repository, and non-v4 scope evidence.
- **A3 / R5-R6:** table-driven classifier tests cover configured live surfaces, documentation/test/governance-only changes, multiple surfaces, and ambiguous high-risk fail-closed behavior.
- **A4 / R7-R9:** replay tests prove stable keys, all-state duplicate detection, one create on first observation, and complete deterministic commissioning issue content.
- **A5 / R10-R12:** tests prove no source mutation, bounded state/receipts, retry after provider failure, overlap replay, and first-start non-backfill behavior.
- Focused tests, scope check, `git diff --check`, required specialist architecture/security/API reviews, and full canonical repository verification must pass on the final source.
- After merge/restart, live commissioning must observe a fresh governed merge and prove one correct intake result before #453 is complete.

## Rollback and recovery

- Before merge: revert the change branch normally.
- After merge but before live commissioning: disable the observer target/configuration or revert the merge; no source issue state needs repair.
- If an incorrect commissioning issue is created, preserve it as evidence and correct/supersede through Work Management rather than deleting it.
- A corrupt local checkpoint is treated as unavailable state; the runtime must fail safely or reinitialize at current time, never silently interpret corruption as permission to backfill.

## Open decisions

None. The parent/child requirements plus current repository authority resolve the material design choices: dedicated `kis-op` lifecycle host, provider-observed merge truth, landed governed scope as source metadata, one machine-readable classification policy, remote-key duplicate suppression, and no source evidence projection until #454.

## Specification review approval

Approved by the operator's explicit `go` after the exact planning-diff architecture review completed with no findings or unknowns. The approved architecture is the dedicated `kis-op` lifecycle observer, provider-observed exact merge identity, landed schema-v4 scope linkage, one machine-readable classification policy, remote-key duplicate suppression, and no source evidence projection until #454.
