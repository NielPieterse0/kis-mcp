# Closeout: Generic Acquisition Envelope

## Implemented scope

- Upgraded KIS external-acquisition authorization settings to schema v2.
- Bound each authorized KIS profile to the exact selected `import-isolate` provider-profile schema version and canonical SHA-256 while keeping provider network/auth/resource semantics provider-owned.
- Added bounded request-schema-v2 scalar arrays for provider-supported list/date iteration; request v1 remains scalar-only.
- Kept current Firecrawl and public HTTP authorizations on request v1 and did not authorize the disabled generic HTTP template or commercial/licensed sources.
- Reconciled the machine-readable settings contract and durable module product specification; ordinary Work HR-002 behavior is unchanged.

## Validation evidence

- Focused checks: `python -m pytest tests/acquisition tests/capabilities/test_registered_acquisition_dispatch.py -vv --tb=short` => 13 passed.
- Cross-repository binding check: checked-in Firecrawl/public HTTP profile schema versions and canonical hashes match the current registered `C:\Projects\import-isolate\policy\provider-profiles.json` records.
- Contract check: Draft 2020-12 validation of `settings/external-acquisition.settings.json` against `contracts/external-acquisition/settings.schema.json` passed.
- Diff checks: `git diff --check` clean; `scripts/change-workflow.ps1 check` reported only the declared change paths.
- Repository verification: local `scripts/verify.ps1` and `scripts/verify.ps1 -SkipDependencySync` exceeded the single-call tool execution window. Neither timeout is represented as a pass; canonical full verification remains an immutable review-head/CI gate.

## Review

- Required frozen-source reviews: `code-quality`, `safety-security`, `architecture`, and `api-contracts` from the declared complexity/risk controls.
- Pre-freeze code-quality and architecture probes reported no findings; final review evidence must be taken after this change record is frozen because later edits invalidate prior fingerprints.

## Git and merge

- Branch: `change/175-generic-acquisition-envelope`
- Worktree: `.work/worktrees/175-generic-acquisition-envelope`
- Base: registered `main` `1365d84de30360b880f95bc5c51101ddeab9006c` / tree `443a77461e5dabdb53cdf0a904c135ea0b8d8baa`.
- Commit: pending frozen-source commit.
- Pull request or merge: pending exact review/verification evidence.
- Cleanup: pending verified merge.

## Residual items

- Work Management exact-target claim/completion for issue #258 was blocked by the live truncated Project inventory defect tracked separately as #269. This change does not bypass or modify that lane.
- Provider execution semantics and the twelve transport/fixture classes are already landed and verified by companion `import-isolate#13`; this change owns only the KIS authorization/contract side.
