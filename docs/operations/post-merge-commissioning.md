# Post-Merge Commissioning

## Authority and scope

This runbook covers the deterministic post-merge observer, commissioning-issue intake, live-verification runner, durable evidence, and source projection owned by `settings/post-merge-commissioning.settings.json`.

The commissioning lifecycle is separate from housekeeping. Housekeeping remains scheduled preview-only and `kis_housekeeping_apply_receipt` remains explicit supervised apply. Commissioning has no housekeeping apply authority.

Only `kis-op` schedules merged-PR observation. `kis-dev` exposes the same commissioning diagnostics and runner contract but does not schedule observer mutations.

Source repository delivery and live commissioning are separate domains. A source issue may remain delivered/Done while its `Live Verification` field is Pending, Failed, or Blocked. Commissioning never rewrites source `Verification`.

## Deterministic merge and obligation identity

Candidate search is discovery only. Each candidate is re-read from GitHub and must report `merged=true`.

The provider-native PR head repository must be the configured governed repository and its ref must be an exact repository-mandated `change/<change-id>` branch. That head ref is corroboration, not merge identity. The observer first exhausts the provider-native PR source-commit SHA list; no SHA from that set may become merge identity, even if its message imitates GitHub's generated merge line. The exact merge SHA is then resolved only from the registered default-branch commit stream and must be the unique non-source commit whose generated first line names the exact PR number and provider-native head branch and whose provider-native committer is GitHub `web-flow`. Git committer time is only a temporal sanity check: sub-minute drift from PR `merged_at` is accepted; a one-minute-or-greater absolute difference is inconsistent provider evidence. Source-commit, identity, timing, or response-shape disagreement is retryable provider evidence.

After resolving that exact merge SHA, the observer requires the merged PR's provider `changed_files` count to be positive and no greater than GitHub's 3,000-file commit-response ceiling. Exact merge-commit file pages are read only until that count is reached; duplicate/non-progressing filenames, early short pages, count overflow, or response-shape disagreement are retryable provider evidence and do not advance the checkpoint. Only after completeness is proven does the observer require exactly one canonical `.work/changes/<change-id>/scope.json` path; that path's change ID remains provisional. The observer resolves the scope path to one non-truncated blob entry from the exact merge tree, reads the file only at the exact merge SHA, and requires the computed Git blob SHA of the returned bytes to match the tree entry. Tree/content mismatch is retryable provider evidence. Only then are schema version 4 and Work source repository/issue identity validated as immutable landed evidence, and only then may a PR-head/scope change-ID disagreement become immutable `scope_identity_mismatch`. Before classification or intake, the observer reads the exact source Work card with history enabled and requires its managed canonical `Change ID` to match the landed change ID; incomplete, non-unique, or mismatched Work evidence is retryable and preserves the checkpoint. Zero or multiple canonical scope paths and blob-proven PR-head/scope change-ID disagreement fail closed as immutable landed evidence.

PR-body text is non-authoritative mutable metadata. `Issue:`, `Change:`, `Tracks`, `Addresses`, closing keywords, titles, commit subjects, and other free-form text are not authority for Work source identity or landed change identity. Historical markers may remain present. The observer does parse only GitHub's exact generated merge first line as one merge-SHA corroboration alongside source-commit exclusion, provider-native `web-flow` identity, and a sub-minute temporal sanity check against `merged_at`. The provider-native PR head ref is accepted only in the closed repository-mandated `change/<change-id>` form to constrain merge selection, and the exact landed scope must later corroborate the same change ID; no free-form branch text is heuristically parsed.

Only immutable landed-governance failures are recorded as bounded `blocked_evidence` outcomes: missing or multiple canonical scope paths, invalid landed schema-v4 scope content, landed scope identity mismatch, or immutable PR-head/scope change-ID mismatch. These outcomes carry a stable error code, create no commissioning issue, and perform no source Project projection. Provider/discovery/configuration uncertainty and incomplete/non-unique/mismatched source Work evidence are not converted to `blocked_evidence`. Classification is machine-owned by the checked-in settings document. Each live surface has path/risk matchers, a runtime instance, a machine-readable refresh rule, and a closed `probe_id` selecting one code-owned read-only probe profile.

Each per-surface obligation key is:

```text
commission:<normalized-owner/repo>:<exact-merge-sha>:<surface-id>
```

Before creation, the observer searches open and closed repository issues for the exact key. Existing matches are reused. A new issue is mutated only once, then its durable result is reconciled through bounded provider confirmation: direct read-back when an issue number is available, deterministic-key search as a fallback, short bounded retry/backoff for transient visibility or response-shape variation, and semantic normalization of harmless text representation differences. Lost or incomplete mutation responses may therefore recover from durable provider evidence without repeating the write. The deterministic title/body contract, commissioning key, and duplicate-prevention identity remain authoritative; unconfirmed, conflicting, or materially different durable content still fails closed and preserves the observer checkpoint for retry.

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

On first observer activation, the current time becomes the repository checkpoint and no historical scan is performed. Subsequent runs search from `checkpoint - overlap_seconds`. The checkpoint advances only after every discovered candidate is accounted either by normal deterministic processing or by a bounded `blocked_evidence` outcome.

Provider response-shape/content failures, invalid or mismatched PR `changed_files` evidence, incomplete/non-unique source Work evidence, source Work `Change ID` mismatch, `pr_not_merged`, missing or ambiguous merge-commit resolution, repository/configuration errors, provider exceptions, budget exhaustion, malformed search envelopes, state corruption, and unexpected runtime errors remain retryable scan failures. Candidate discovery has its own bounded external-read counter, and each discovered candidate receives an independent `max_external_reads` allowance; with the current single-read discovery path, the configured scan therefore permits at most `1 + (max_candidates * max_external_reads)` external reads. Candidates are processed deterministically newest-first by pull request number within the bounded discovery window, so fresh governed merges are evaluated before older backlog can consume scan-wide mutation authority. All candidates continue to share one scan-wide `max_mutations` budget. A retryable failure while processing one discovered candidate, including exhaustion of that candidate's external-read allowance, is recorded as bounded `unresolved_candidate` evidence containing only its PR number, exception type, and stable error code when available; independently valid later candidates in the same bounded scan are still processed. Any unresolved candidate keeps the run incomplete and preserves the previous checkpoint, so continuation never silently discards unresolved evidence. Search-envelope/configuration failures and exhausted scan-wide mutation budgets remain whole-scan failures. Malformed checkpoint state fails closed; recovery retains the corrupt checkpoint as timestamped evidence, establishes a new current-time checkpoint, performs no historical backfill, and reports an incomplete recovery run. Do not edit checkpoints to force history; #455 owns deterministic historical backfill.

## Live release verification

After a commissioning runtime change merges, restart/refresh `kis-op` so its source revision contains the merge. Do not alter the observer checkpoint.

A fresh governed runtime-affecting merge after the activation boundary must be discovered independently by the observer. Verify its exact merge SHA, classified live surface, deterministic commissioning key, generated/reused issue, observer receipt, and source Pending projection.

Transition/claim the generated commissioning issue through canonical Work Management, then invoke `kis_post_merge_commissioning_run` through the live `kis-op` runtime. A successful smoke must retain the execution receipt and aggregate receipt, set source `Live Verification = Passed`, complete the commissioning Work item, and close only that commissioning issue.

If the runner reports `runtime_refresh_required`, perform the supervised `kis-op` restart and explicitly retry the same issue. Failed or Blocked evidence remains visible and must not be rewritten as source delivery failure.