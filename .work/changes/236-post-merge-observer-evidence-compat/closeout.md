# Closeout: Post Merge Observer Evidence Compat

## Implemented scope

- Resolve merged-change identity without PR-body issue/change markers.
- Require a same-repository governed PR head, enumerate and exclude every provider-native PR source-commit SHA, then accept one default-branch merge candidate only with the exact PR/head generated line and GitHub `web-flow` identity; use committer time only as a temporal sanity bound, accepting sub-minute drift from provider `merged_at` and rejecting a one-minute-or-greater mismatch.
- Require complete exact merge-file enumeration against provider `changed_files` before selecting one canonical scope path.
- Bind scope bytes to the exact merge-tree blob SHA before schema/identity validation; only after that proof can PR-head/scope disagreement be immutable.
- Corroborate the proven landed change with the exact source Work card's managed `Change ID` before classification or intake.
- Keep PR-body text non-authoritative; convert only proven immutable landed-governance errors to bounded `blocked_evidence`; re-raise provider/discovery/configuration/Work uncertainty so the checkpoint remains retryable.
- Bound source-commit pagination, merge/file pagination, tree entries, wrapper depth, scope bytes, and JSON recursion behavior.
- Reconcile operator documentation and the minimal current-product `SPEC.md` authority after safely retiring Change 232's unimplemented orphan claim.

## Validation evidence

- `uv run --offline --no-sync pytest tests/post_merge_commissioning -q`: 171 passed on the live-acceptance timing-amended executable state.
- Ruff on changed commissioning Python/tests: passed.
- `git diff --check`: passed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed with only the 13 Change 236 owned paths after adding the released `SPEC.md` authority.
- Live PR #473: provider source-commit list contains `ce558389...`; default-branch merge is distinct `3e060f67...`, reports outer committer `web-flow`, exact generated PR/head line, and committer timestamp equal to `merged_at`.
- Live PR #473: `changed_files=9`; exact merge enumeration returned 9 files; landed scope blob `81b05330...` matched the exact downloaded scope bytes.
- Live historical Work #409: complete, non-truncated board evidence reports canonical `Change ID = 235-registered-project-schema-utf8`, matching PR #473 governed head/scope.
- First post-merge acceptance after PR #481 exposed PR #434 with provider `merged_at=2026-08-20T23:09:53Z` and the otherwise exact GitHub `web-flow` merge commit at `2026-08-20T23:09:52Z`; the old equality rule falsely returned `merge_commit_missing`. The amended resolver accepts this 1-second drift and rejects an absolute difference of one minute or more.

## Review

- Final automated architecture review on fingerprint `57267cee3bb781eda865928e58b4e9c295b2f566080789114aeba2bbf9a9aee7`: clean after correcting pre-provenance checkpoint classification and moving PR-head/scope mismatch after blob proof.
- Final automated documentation review found one wording contradiction; corrected so generated merge-line parsing is merge-SHA corroboration only, never Work/landed source-identity authority.
- Code-quality, API-contract, test-quality, and safety-security projectors exceeded their bounded evidence window and invoked no backend. Required exact-diff manual fallbacks reviewed the complete changed source/tests plus runtime-service checkpoint implementation and found no remaining actionable issue.
- Manual safety fallback specifically verified after the live-acceptance amendment: the executable delta changes only exact-second time equality to an absolute `<60s` sanity bound. Source PR SHAs are still excluded before candidacy; candidates still require the exact generated PR/head line and provider-native `web-flow` identity; uniqueness remains mandatory; complete changed-file enumeration, exact merge-tree/blob proof, PR-head change ID, and source Work `Change ID` corroboration remain unchanged. Therefore the tolerance cannot independently establish merge identity or admit a source commit, and `>=60s` disagreement still produces retryable `merge_commit_missing` with the checkpoint preserved. No new mutation, receipt, or persisted-evidence surface is introduced.
- Manual API fallback verified the live `github_pull_request_read(get_commits)`, `github_list_commits(... fields=[sha,commit,committer])`, `github_get_repository_tree`, exact file-content, and `project_management_board_data` shapes used by the resolver.
- Manual test fallback confirmed direct regressions for markerless bodies, source-commit impersonation, exact merge corroboration, changed-file/blob bounds, pre-provenance retryability, blob-proven immutable mismatch, Work corroboration uncertainty, processor allowlist, checkpoint preservation/advancement, and replay.
- After `SPEC.md` reconciliation, final architecture and documentation automation correctly refused incomplete projected evidence on exact commit fingerprint `7fa3605dc329394532fa4ae525111aefd2bb89b36b55012eb325934ffa76cd8e` because `commissioning/evidence.py` was omitted. The required complete exact-diff fallback found no new issue at that revision; live acceptance later superseded only the exact-second time condition with bounded sub-minute temporal sanity while preserving source-SHA exclusion, exact PR/head/`web-flow` merge proof, changed-file completeness, exact blob proof, PR-head + Work `Change ID` corroboration, four-code immutable `blocked_evidence` allowlist, and retry-preserved checkpoint semantics.

## Git and merge

- Branch: `change/236-post-merge-observer-evidence-compat`
- Worktree: `.work/worktrees/236-post-merge-observer-evidence-compat`
- First published source head: `95b9d4cec38f4a84b25afa8f4119bac7dd8c5cd6`; PR #481 exact-head Actions run `32751107415` passed and Work merge-readiness was `ready=true` with zero blockers/advisories.
- First landing: PR #481 merged as `6dd3e74e21678cbd9751081e86d9acf56304da25`; local/default/tracking authority was aligned and `kis-dev` auto-refreshed to that landed revision.
- Live acceptance then failed only on the exact-second timestamp rule described above; the timing-amended follow-up source head / PR / exact-head CI are pending publication.
- Change 232 ownership blocker: cleared before publication; its uncommitted draft record is preserved in recoverable quarantine and its clean ancestral orphan worktree/branch was safely retired.
- Cleanup: pending verified merge and live acceptance.

## Residual items

- Change 232 ownership is released, the required minimal `SPEC.md` reconciliation is complete, and the reconciled tree is covered by the recorded exact-diff architecture/documentation fallback.
- Post-merge live acceptance requires the landed runtime and an explicitly supervised `kis-op` refresh if the running `kis-op` image is stale; no automatic `kis-op` lifecycle action is authorized.
- Work #474 remains open until live observer acceptance and final cleanup complete.
