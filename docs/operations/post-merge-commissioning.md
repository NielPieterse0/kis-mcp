# Post-Merge Commissioning Observer

## Authority and scope

This runbook covers the deterministic post-merge observer and commissioning-issue intake owned by `settings/post-merge-commissioning.settings.json`.

The observer is separate from housekeeping. Housekeeping remains scheduled preview-only and `kis_housekeeping_apply_receipt` remains explicit supervised apply. The commissioning observer has no housekeeping apply authority.

Only `kis-op` schedules post-merge observation. `kis-dev` exposes the same read-only diagnostic tools but does not schedule commissioning mutations.

This slice creates deterministic commissioning issues only. It does not execute live verification or project `Live Verification` evidence; that lifecycle belongs to the later commissioning-runner work. Historical backfill is also separate.

## Deterministic identity

Candidate search is discovery only. Each candidate must be re-read from GitHub and report `merged=true`.

The exact merge SHA is resolved from the registered default branch and must be the unique merge commit whose message identifies the same pull request. The PR source head is never accepted as merge identity.

The PR body must contain exactly one `Issue: #N` marker and one `Change: <change-id>` marker. The observer then reads `.work/changes/<change-id>/scope.json` at the exact merge SHA and requires schema version 4 plus matching Work source repository/issue identity.

## Classification and intake

Classification is machine-owned by the checked-in settings document. It uses only exact changed paths plus governed change risk triggers.

Configured live surfaces produce commissioning obligations. Documentation/test/governance-only changes with no configured live surface are `not_required`. A configured ambiguous high-risk trigger with no resolvable surface is `blocked_ambiguous`; it is never silently interpreted as not required.

Each obligation key is:

```text
commission:<normalized-owner/repo>:<exact-merge-sha>:<surface-id>
```

Before creation, the observer searches repository issues across open and closed state for the exact key. A match is reused as the existing obligation. A newly created issue is re-read and must retain the same key before the candidate is considered accounted for.

Commissioning intake does not reopen, close, or otherwise rewrite the source delivery issue.

## Startup and checkpoint behavior

The observer persists its state beneath the configured KIS state root and `state_namespace`. Checkpoints are repository-specific and receipts are retention-bounded.

On first activation, the observer records the current time as the checkpoint and performs no historical scan. This is intentional: explicit historical assessment/backfill is a separately governed operation.

Subsequent runs search from `checkpoint - overlap_seconds`. A checkpoint advances only after the bounded candidate scan completes and every discovered candidate has a durable outcome. Provider, evidence, budget, or intake failure leaves the prior checkpoint in place so the overlap window can replay safely.

## Diagnostics

Use the read-only tools:

- `kis_post_merge_commissioning_status` — reports configured host/current instance, scheduler activation, target repository/default branch, checkpoint state, and checkpoint time.
- `kis_post_merge_commissioning_receipt` — reads one persisted bounded run receipt by deterministic receipt ID.

A run receipt contains only bounded identities, classification/intake references, counts, timestamps, and typed error names. Provider response bodies, exception messages, credentials, prompts, and free-form logs are not persisted.

The observer enforces configured external-read and mutation budgets for each run. Exceeding either budget fails the run without advancing the checkpoint.

## Corrupt checkpoint recovery

Malformed checkpoint state fails closed. The observer retains the corrupt checkpoint as timestamped recovery evidence, establishes a new current-time checkpoint, performs no backfill, and reports an incomplete recovery run.

Do not edit a checkpoint to force historical scanning. Use the separately governed backfill workflow when historical merges must be assessed.

## Live release verification

After a change that introduces or changes this observer is merged, restart/refresh `kis-op` so the runtime generation includes the new source and settings.

First activation should show an initialized current-time checkpoint with no historical candidate processing. Then land one fresh governed runtime-affecting PR after that checkpoint. The observer must discover the merge independently of the KIS merge command, resolve its exact merge SHA and landed scope, classify the configured live surface, and create or reuse exactly one commissioning issue for each deterministic key.

Record the resulting observer receipt, source PR, exact merge SHA, commissioning key, and commissioning issue reference in the governing issue/change evidence. Failure leaves the governing work incomplete; do not reinterpret the already-merged source delivery as unmerged.
