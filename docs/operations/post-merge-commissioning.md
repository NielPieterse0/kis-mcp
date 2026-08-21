# Post-Merge Commissioning

## Authority and scope

This runbook covers the deterministic post-merge observer, commissioning-issue intake, live-verification runner, durable evidence, and source projection owned by `settings/post-merge-commissioning.settings.json`.

The commissioning lifecycle is separate from housekeeping. Housekeeping remains scheduled preview-only and `kis_housekeeping_apply_receipt` remains explicit supervised apply. Commissioning has no housekeeping apply authority.

Only `kis-op` schedules merged-PR observation. `kis-dev` exposes the same commissioning diagnostics and runner contract but does not schedule observer mutations.

Source repository delivery and live commissioning are separate domains. A source issue may remain delivered/Done while its `Live Verification` field is Pending, Failed, or Blocked. Commissioning never rewrites source `Verification`.

## Deterministic merge and obligation identity

Candidate search is discovery only. Each candidate is re-read from GitHub and must report `merged=true`.

The exact merge SHA is resolved from the registered default branch and must be the unique merge commit whose message identifies the same pull request. The PR source head is never accepted as merge identity.

The PR body must contain exactly one `Issue: #N` marker and one `Change: <change-id>` marker. The observer reads `.work/changes/<change-id>/scope.json` at the exact merge SHA and requires schema version 4 plus matching Work source identity.

Classification is machine-owned by the checked-in settings document. Each live surface has path/risk matchers, a runtime instance, a machine-readable refresh rule, and a closed `probe_id` selecting one code-owned read-only probe profile.
Each per-surface obligation key is:

```text
commission:<normalized-owner/repo>:<exact-merge-sha>:<surface-id>
```

Before creation, the observer searches open and closed repository issues for the exact key. Existing matches are reused; newly created issues are re-read and must retain the deterministic title/body contract.

## Source classification projection

After exact classification and intake, the observer projects only the three live fields through canonical `project_management_reconcile` using fresh Project revision evidence:

- required obligations → `Live Verification = Pending`, deterministic source Commissioning Key, and sorted commissioning-issue linkage;
- no obligations → `Live Verification = Not Required` and no Commissioning Key;
- ambiguous high-risk classification → `Live Verification = Blocked`, no invented key, and compact exact-merge classification evidence.

`Verification` is never included in this reconciliation write set.

For a single required surface, the source Commissioning Key is the exact per-surface key. For multiple surfaces, source projection uses `commission:<repo>:<merge-sha>:set-<digest24>`, with the digest derived deterministically from the sorted obligation keys.

## Runner admission and runtime generation

`kis_post_merge_commissioning_run` accepts only repository, commissioning issue number, execution owner, and optional explicit retry. It does not accept arbitrary operation names, commands, predicates, procedures, or refresh actions.

Before any live proof, the runner re-reads and strictly parses the generated issue, re-resolves the source PR/merge/scope, reclassifies the merge, freezes the matching obligation, and requires exactly one current Active Work card claimed by the supplied execution owner.
For `refresh_rule=none`, no runtime-generation ancestry check is required. For `refresh` or `restart`, the runner reads the real `kis_health` path, verifies the configured runtime identity, and checks that the frozen merge is an ancestor of the running source revision in the governed local repository.

A stale generation records `Blocked/runtime_refresh_required` before the live probe. The runner never stops or restarts its own hosting `kis-op` process. Restart/refresh is performed through the normal supervised launcher, then the same obligation is retried explicitly with `retry=true`.

## Closed live probe profiles

The settings `probe_id` is a closed vocabulary. Current profiles dispatch only through `execute_read_action`:

- `coordinator-work-board` → exact claimed commissioning card through `project_management_board_data`;
- `gateway-health` → ready runtime identity/source revision through `kis_health`;
- `housekeeping-status` → active host/schedulers through `kis_housekeeping_status`;
- `provider-status` → ready provider platform with zero unavailable providers through `kis_provider_status`;
- `post-merge-observer-status` → active/fresh observer and scheduler through `kis_post_merge_commissioning_status`;
- `work-management-contract` → canonical distinct source/live verification domains through `project_management_contract`.

Unknown profiles and mutation-capable/generic executable probes are not accepted.

## Durable execution and retry

Per-obligation execution state and immutable receipts are stored beneath the existing commissioning state namespace. Each attempt freezes its contract fingerprint, attempt number, phase, result, and proof receipt reference.

A completed Passed obligation replays without another probe or duplicate mutation. Failed and Blocked outcomes also replay unchanged unless the caller explicitly uses `retry=true`; retry first revalidates exact obligation identity and then creates the next attempt.

Interrupted execution resumes from the persisted phase. In particular, a persisted proof is not re-probed merely because source projection or Work closeout was interrupted.
## Aggregate source evidence and terminal lifecycle

After proof persistence, the runner recomputes the complete classifier obligation set for the frozen merge. Latest per-obligation states are aggregated with deterministic precedence: Failed > Blocked > Pending > Passed; Passed requires every required obligation to have passed.

The aggregate receipt contains the exact merge identity and ordered obligation key/state/receipt references. Project `Live Verification Evidence` stores only a compact `commissioning-evidence:<sha256>` reference to that durable receipt.

Terminal behavior is intentionally asymmetric:

- Passed → source aggregate projection, canonical `project_management_complete_work`, then close only the generated commissioning issue;
- Failed → source aggregate becomes Failed while commissioning Work/issue remain open for explicit retry;
- Blocked → source aggregate becomes Blocked and commissioning Work transitions to Blocked; the issue remains open.

Source delivery remains closed/delivered throughout these outcomes.

## Diagnostics

Use the commissioning tools:

- `kis_post_merge_commissioning_status` — read observer host, scheduler/checkpoint, and freshness status;
- `kis_post_merge_commissioning_receipt` — read one bounded observer or aggregate/execution receipt by deterministic receipt ID;
- `kis_post_merge_commissioning_execution` — read the latest bounded execution state/proof for one commissioning key;
- `kis_post_merge_commissioning_run` — approval-required execution of one currently claimed commissioning issue.

Receipts retain bounded identities, hashes, selected assertions, timestamps, and typed result/error codes. They do not retain credentials, prompts, free-form runtime logs, or complete provider response bodies.

## Startup, checkpoint, and recovery

On first observer activation, the current time becomes the repository checkpoint and no historical scan is performed. Subsequent runs search from `checkpoint - overlap_seconds`; the checkpoint advances only after the bounded scan and all discovered candidates complete deterministic processing.

Malformed checkpoint state fails closed. Recovery retains the corrupt checkpoint as timestamped evidence, establishes a new current-time checkpoint, performs no historical backfill, and reports an incomplete recovery run. Do not edit checkpoints to force history; #455 owns deterministic historical backfill.
## Live release verification

After a commissioning runtime change merges, restart/refresh `kis-op` so its source revision contains the merge. Do not alter the observer checkpoint.

A fresh governed runtime-affecting merge after the activation boundary must be discovered independently by the observer. Verify its exact merge SHA, classified live surface, deterministic commissioning key, generated/reused issue, observer receipt, and source Pending projection.

Transition/claim the generated commissioning issue through canonical Work Management, then invoke `kis_post_merge_commissioning_run` through the live `kis-op` runtime. A successful smoke must retain the execution receipt and aggregate receipt, set source `Live Verification = Passed`, complete the commissioning Work item, and close only that commissioning issue.

If the runner reports `runtime_refresh_required`, perform the supervised `kis-op` restart and explicitly retry the same issue. Failed or Blocked evidence remains visible and must not be rewritten as source delivery failure.