# Change Specification: Post-Merge Observer Evidence Compatibility

- **Change ID**: `236-post-merge-observer-evidence-compat`
- **Work item**: `#474`
- **Development level**: Complex (`scope.json` complexity `large`)
- **Status**: Live-acceptance timing amendment approved — implementation reauthorized 2026-08-24
- **Risk profile**: architecture boundary, external action, persistent observer state, public contract

## Outcome and defect evidence

Restore deterministic post-merge commissioning observation for governed PRs whose bodies omit the older strict `Issue: #N` + `Change: <change-id>` marker pair, without weakening exact merged-change identity or letting one deterministically malformed candidate wedge the observer checkpoint forever.

The live `kis-op` observer reports an incomplete receipt with `MergeEvidenceError`, `candidate_count=6`, and zero outcomes. The six post-checkpoint merged PRs (#434, #466, #468, #470, #472, #473) use current `Tracks #...` / `Addresses #...`-style bodies and omit the strict pair. PR #456 retains the older strict pair and previously commissioned successfully.

## Authority and scope

Authoritative inputs are `#474`, parent commissioning work `#419/#453`, the approved Change 228 observer contract, current `SPEC.md`, `settings/post-merge-commissioning.settings.json`, `AGENTS.md`, and the live defect evidence above.

Owned executable paths are `src/kis_mcp/commissioning/evidence.py` and `src/kis_mcp/commissioning_runtime/processor.py`, with focused commissioning tests, operator documentation, and the smallest required current-product reconciliation in `SPEC.md`. Change 232 was confirmed to contain no committed implementation, its untracked draft record was preserved in recoverable quarantine, and its already-ancestral orphan worktree/branch was safely retired before Change 236 claimed `SPEC.md`.

No housekeeping authority, commissioning runner semantics, Work source delivery state, Project schema, classifier policy, commissioning-key derivation, or historical backfill authority changes in this slice.

## Existing implementation evidence

The pre-change `MergedChangeResolver._merge_sha` already derived the exact merge SHA from a bounded default-branch commit window and required one merge message identifying the same PR. `_changed_paths` already re-read that exact SHA and rejected SHA mismatch or missing file evidence. `_scope_document` already required `schema_version == 4`. The original defect was ordering: `resolve()` called `_parse_markers()` before merge/scope resolution and therefore could not reach those exact-evidence checks for markerless PRs.

The pre-change `CommissioningCandidateProcessor` did not catch `MergeEvidenceError`; the runtime service appends every returned processor dictionary and advances the checkpoint only after the whole candidate loop returns normally. The implemented repair therefore uses a narrow code allowlist for accounted immutable evidence failures, while all other provider/runtime evidence errors continue through the service's existing incomplete-run path.

Observer run receipts remain top-level `schema_version: 1`. Candidate outcomes are embedded bounded dictionaries rather than a separately versioned persisted schema; Change 236 adds one explicit outcome kind/value without changing receipt identity, storage, or existing successful-outcome fields.

## Safety-review amendment

The first implementation pass exposed a material availability weakness during exact-diff safety review. The configured observer overlap is finite, so treating mutable PR-body marker text or transient provider-evidence failures as an accounted `blocked_evidence` outcome can advance the checkpoint and let the candidate age out without another automatic attempt. The revised design therefore removes PR-body text from admission authority and narrows `blocked_evidence` to immutable landed-governance defects only. Provider/discovery uncertainty remains retryable and must preserve the checkpoint.

The original first-pass implementation was superseded before publication. The current implementation follows this approved amendment and includes provider-completeness and exact-blob provenance checks before immutable evidence classification.

A later exact-diff safety review identified one remaining provenance gap: a blob-proven scope can still self-assert an unrelated Work issue unless the observed PR and Work command plane independently corroborate the same governed change. The approved 2026-08-24 amendment therefore requires the provider-native PR head ref to equal the repository-mandated `change/<change-id>` branch and requires the exact source Work card to report the same managed canonical `Change ID`. PR prose remains irrelevant. Incomplete or mismatched Work evidence is retryable because the Project projection is externally observed state.

Post-merge live acceptance of PR #481 then reproduced the still-wedged observer on historical PR #434. Provider `merged_at` was `2026-08-20T23:09:53Z` while the unique otherwise-valid GitHub `web-flow` merge commit was stamped `2026-08-20T23:09:52Z`. Exact-second equality therefore produced a false `merge_commit_missing` despite all stronger identity signals agreeing. The approved live-acceptance amendment makes time corroborating evidence only: absolute drift below one minute is accepted, while one minute or more is treated as an obvious temporal mismatch and remains retryable provider evidence.

## Requirements and invariants

- **R1 — Exact merge truth remains mandatory.** Candidate discovery remains non-authoritative; the PR must re-read `merged=true`. Its provider-native same-repository head ref must be the governed `change/<change-id>` branch. The resolver first exhausts the provider-native PR source-commit SHA list; no SHA in that set may become merge identity. The exact merge SHA must then resolve uniquely from the registered default-branch commit stream using the exact PR number/head branch pair, provider-native GitHub `web-flow` committer identity, and a Git committer timestamp that is temporally consistent with the PR `merged_at`: sub-minute drift is permitted, while an absolute difference of one minute or more is treated as inconsistent provider evidence. Any provider-shape, source-commit, or identity disagreement remains retryable.
- **R2 — Complete exact changed-file evidence precedes source identity.** The merged PR's provider-reported `changed_files` count must be positive and no greater than the GitHub commit provider ceiling of 3,000 files. The resolver reads exact merge-commit file pages only until that count is reached, rejects duplicate/non-progressing pages and early short pages, and requires the resulting distinct-file count to equal `changed_files` before choosing the landed change scope. Count/shape/bound disagreement is retryable `provider_evidence_invalid`. Only after completeness is established does the resolver accept exactly one changed path matching `.work/changes/<change-id>/scope.json`; zero or multiple canonical scope paths are immutable fail-closed evidence.
- **R3 — Proven landed schema-v4 scope is source identity authority with independent corroboration.** The selected scope path is resolved to exactly one non-truncated blob entry from the exact merge tree. The scope content is read only at the exact merge SHA, its computed Git blob SHA must match that tree entry, and only then may JSON/schema/identity validation be treated as immutable landed evidence. A tree/content provenance mismatch is retryable `provider_evidence_invalid`. The proven landed scope must be schema version 4 and contain a valid change ID plus Work source repository, positive issue number, and `source_kind=issue`; those values are accepted only when the provider-native PR head ref is exactly `change/<change-id>` and the uniquely observed source Work card reports the same canonical `Change ID`.
- **R4 — PR body is non-authoritative mutable metadata.** Observer admission and source identity must not parse, require, reject, or otherwise gate on PR-body markers. Historical strict markers may remain present, but only the exact landed scope plus machine-readable corroboration controls source linkage. This prevents mutable PR text from suppressing commissioning after checkpoint advancement.
- **R5 — No heuristic issue parsing.** `Issue:`, `Change:`, `Tracks`, `Addresses`, closing keywords, PR title text, commit subjects, and conversational text are not source-identity authority. Because `AGENTS.md` mandates the closed `change/<change-id>` branch form, the exact provider-native PR head ref may establish the candidate governed change ID and constrain exact merge-commit selection; the unique landed scope path and scope document must later corroborate that same ID. No free-form branch parsing, fuzzy matching, or LLM parsing is allowed.
- **R6 — Only immutable landed-governance defects are accounted evidence failures.** `blocked_evidence` is reserved for stable exact-merge facts such as zero/multiple canonical scope paths, invalid landed schema-v4 scope content, landed scope identity mismatch, or an immutable PR-head/scope change-ID mismatch. The outcome carries only PR number, stable machine error code, and empty commissioning/issue lists; it performs no intake or source projection.
- **R7 — Provider/discovery/Work uncertainty remains retryable.** Provider exceptions and provider-shape/content transport failures, incomplete or non-unique source Work evidence, Work `Change ID` mismatch, `pr_not_merged`, missing/ambiguous merge-commit resolution, repository/configuration errors, budget exhaustion, malformed candidate-search envelopes, state corruption, and unexpected runtime failures must remain unaccounted. They produce an incomplete run and preserve the prior checkpoint.
- **R8 — Error typing must preserve R6/R7.** Provider response decoding/shape failures must use provider-evidence error codes rather than landed-scope-invalid codes. The processor may convert only the explicit deterministic landed-governance code set to `blocked_evidence`; every other `MergeEvidenceError` is re-raised.
- **R9 — Checkpoint advancement requires every candidate to be accounted.** Successful classification/intake outcomes and R6 bounded immutable-governance failures are accounted; every R7 failure is not. The checkpoint advances only when every discovered candidate in the bounded scan is accounted.
- **R10 — Existing marker-bearing PRs remain behaviorally compatible.** A historical PR with strict markers and a valid unique landed scope resolves to the same source/change identity as before, but the marker text itself no longer gates admission. Existing commissioning issue identity, classifier semantics, source projection, duplicate suppression, and runner revalidation remain unchanged.
- **R11 — Evidence remains bounded and non-sensitive.** Filtered merge-tree entries, provider wrapper depth, and encoded/decoded scope content size are locally bounded before hashing/parsing; boundary violations are retryable provider evidence. Observer receipts may persist PR number, classification/outcome kind, stable error code, exact identities that were safely resolved, commissioning keys, and issue numbers; they must not persist PR bodies, provider response bodies, exception detail, credentials, or free-form logs.
- **R12 — Documentation states the revised authority precisely.** The operator runbook must describe unique landed scope identity, PR-body non-authority, the narrow immutable-governance `blocked_evidence` set, and the distinction between accounted evidence failures and retryable provider/discovery failures.

## Architecture and data flow

1. Search bounded merged-PR candidates as today; re-read each candidate and require `merged=true`, a same-repository governed `change/<change-id>` head ref, and valid provider merge metadata.
2. Exhaust the provider-native PR source-commit SHA list, then resolve the unique default-branch merge commit only from a SHA outside that source set whose generated merge line matches the exact PR number/head branch, whose provider-native committer is GitHub `web-flow`, and whose Git committer timestamp is within less than one minute of PR `merged_at`. A one-minute-or-greater timestamp difference is inconsistent and remains retryable provider evidence. Then exhaust its changed-file pages and require the enumerated distinct-file count to equal the merged PR's positive provider `changed_files` count; any identity/count/shape disagreement remains retryable.
3. Only after changed-file completeness is proven, select exactly one changed schema-v4 scope path; its change ID is provisional until blob provenance succeeds.
4. Resolve the selected scope to its exact non-truncated merge-tree blob SHA, read it at the exact merge SHA, and require the computed Git blob SHA of the returned bytes to match the tree entry.
5. Only after blob provenance succeeds, validate schema and source repository/issue/kind from the landed scope, require the proven landed change ID to equal the provider-native PR head change ID, then read the exact source Work card with history enabled and require its canonical `Change ID` to match the landed change ID. Do not parse PR-body text for admission or source identity.
6. On valid evidence, run the existing classifier, intake, and source-projection path unchanged.
7. Convert only the explicit immutable landed-governance error codes to bounded `blocked_evidence`; re-raise provider/discovery/configuration/Work evidence errors.
8. Let the runtime service advance its checkpoint only after every candidate returns an accounted outcome; any re-raised/transient exception retains the existing incomplete-run behavior.

## Failure and recovery semantics

An immutable landed-governance defect is not successful commissioning. It is a fail-closed observed outcome that records why no classification/intake occurred and allows unrelated later merges to continue. Recovery after checkpoint advancement is explicit repair/backfill under #455 or normal rediscovery if the provider surfaces the candidate again; mutable PR text is never a blocker.

Provider/discovery/configuration uncertainty and source Work corroboration uncertainty remain unaccounted and therefore preserve the prior checkpoint for retry. No new persistent schema is required; existing bounded run receipts carry the additional outcome/error fields. Rollback is a normal repository revert plus supervised runtime refresh. Existing checkpoints and commissioning issues remain valid.

## Acceptance and release evidence

- **A1 / R1-R5:** resolver tests prove markerless and marker-bearing PR bodies resolve from one exact matching schema-v4 scope only when the provider-native PR head ref is the mandated `change/<change-id>` and the exact source Work card independently reports the same `Change ID`; malformed/partial/duplicate/contradictory PR marker text does not alter admission; zero/multiple scope paths, immutable PR-head/scope mismatch, wrong source repository, non-positive source issue identity, wrong source kind, and invalid landed scope fail closed.
- **A2 / R6-R9:** processor/runtime tests prove only explicit immutable landed-governance error codes yield bounded `blocked_evidence`, later candidates continue, and a fully accounted scan advances the checkpoint.
- **A3 / R7-R8:** tests prove provider-shape/content errors, incomplete/non-unique source Work evidence, Work `Change ID` mismatch, `pr_not_merged`, merge-commit resolution failures, provider exceptions, budget/search failures, and unexpected processor failures keep the run incomplete and preserve the checkpoint.
- **A4 / R10-R11:** regression tests prove marker-bearing PRs resolve to the same exact landed identity, classification/intake/projection output and duplicate suppression remain unchanged, and receipts contain no provider/body detail.
- **A5 / R12:** `docs/OPERATIONS.md` and `docs/operations/post-merge-commissioning.md` describe the implemented operator semantics without duplicating product architecture; after Change 232 ownership was safely released, `SPEC.md` was minimally reconciled to the same current-product authority and checkpoint semantics.
- Focused commissioning tests, Ruff for changed Python, `git diff --check`, governed scope check, and required architecture/API/security/code/test/documentation reviews must pass before publication.
- Exact-head GitHub Actions and Work merge-readiness must pass before merge.
- After landing and `kis-dev` auto-refresh, the live observer code must be verified without touching `kis-op` lifecycle automatically. `kis-op` refresh remains explicitly supervised when live observer acceptance requires the new code image.
- Live acceptance requires the observer to account the currently wedging markerless governed merges without an unhandled `MergeEvidenceError` and then correctly process a fresh governed runtime-affecting merge through the exact landed-scope path.

## Out of scope

- Historical commissioning backfill owned by #455.
- Rewriting existing PR bodies solely to add markers.
- Parsing `Tracks`, `Addresses`, closing keywords, titles, branch names, or commit text as source identity.
- Altering commissioning classifier rules, key format, runner probe profiles, or source `Verification`.
- Changing housekeeping or adding unattended `kis-op` restart authority.

## Approval gate

This change amends the previously approved Change 228 R4 source-linkage contract and changes checkpoint recovery semantics for deterministic evidence failures. The finalized specification and implementation plan therefore require explicit human approval before production-code or operator-documentation implementation begins.