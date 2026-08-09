# Closeout: Discover Persistent Memory Closeout

- **Change ID:** `084-discover-persistent-memory-closeout`
- **Development level:** Complex
- **Result:** implementation complete; verified and prepared for governed integration

## Implemented scope

- Added shared `kis_mcp.evidence` persistence with bounded SHA-256 manifests, atomic publication, conflict/corruption detection, recoverable staging/pointer retention, and retained generations.
- Added registered-project-scoped Discover Code/Symbol/Relationship persistence with worktree, Git/source, settings/schema/parser, and semantic-provider fingerprints.
- Routed Discover inspect/context/impact/analyze through one `ProjectIntelligenceService` with cold build, warm reuse, stale/corrupt refresh, bounded outputs, provenance, freshness, truncation, and deterministic fallback.
- Preserved Work Management review evidence contracts while moving persistence onto the shared evidence primitive.
- Reconciled pinned Context7 `3.2.5` and Serena `1.6.1` into current Provider runtime without transplanting superseded 040 server/Tools composition.
- Serena contributes only normalized read-only semantic evidence to Discover; deterministic local parsing remains authoritative fallback.
- Completed HR3-07 Serena memory safety for the proven pinned artifact set: quarantine intercepts deletion, does not forward provider delete, restores recoverably, and verifies restart/catalogue/content/hash consistency.
- Selectively absorbed still-valid 040 command/shell resolver behavior and recorded 040 as absorbed and superseded by 084.

## Review

- Exact-scope review found one blocking import-order defect: `providers.platform` imported the capability package before its own exported provider symbols were initialized, creating a fresh-interpreter cycle through `workflows.platform`.
- RED evidence: `tests/providers/test_platform_import_isolation.py` failed in a fresh interpreter, and `test_platform_composition.py` also failed independently on both current `main` and pre-fix 084.
- Resolution: capability contracts/normalization are imported lazily only where provider capability/readiness composition executes; Provider platform can now initialize independently.
- GREEN evidence: fresh-interpreter import regression plus platform composition tests pass independently.
- Direct review found no remaining blocking correctness, policy, secret-handling, recovery, scope, or modularity issue; `git diff --check` is clean and no TODO/FIXME residue or generic Discover memory CRUD surface remains.

## Validation evidence

- Current `main` reconciliation: 084 fast-forwarded from `f35a868` to `aecde786`; the six intervening `main` commits touched no 084 working paths.
- Change scope: `pwsh -NoProfile -File scripts/change-workflow.ps1 check` passed for the declared 084/040 absorption paths.
- Focused exact-scope suite passed after the import-isolation fix, including evidence, project intelligence, impact/settings, Context7/Serena, Provider composition/runtime, resolver, Desktop Commander, and shell-parser regressions.
- Architecture/modularity focused suite passed.
- Canonical `pwsh -NoProfile -File scripts/verify.ps1` passed in the locked offline environment before final closeout metadata edits: full pytest reached 100% with exit 0; configuration, interpreter, dependencies, Python syntax, change governance, line endings, and exact HR-001/HR-002/HR-003 verification passed.
- A final canonical verifier rerun is required after these metadata edits and before commit; integration must stop if it is not green.

## Provider commissioning evidence

- Fresh bounded smoke `scripts/run-provider-live-smoke.py` passed on 2026-08-09 after reconciliation.
- Context7: pinned `3.2.5`, local MCP startup succeeded and exact `resolve-library-id` / `query-docs` discovery passed. `external_document_query_exercised=false` by design; commissioning does not bypass HR-002.
- Serena: pinned `1.6.1`, `UV_OFFLINE=1`, startup/tool discovery and semantic overview passed across restart; quarantine was not forwarded as delete; restored SHA-256 matched; memory catalogue/content remained consistent.
- Commissioning state and recoverable quarantine evidence remain beneath `C:\Projects\.kis-mcp`; no credentials or repository secrets are recorded in the evidence file.

## Specialist review limitation

- `review_change_with_agent` was attempted using the configured/default backend and returned `AGENT_BACKEND_UNAVAILABLE`; explicit alternate backend names were not configured.
- The repository review contract was therefore performed directly. No unavailable specialist result is represented as a pass.

## Recovery and cleanup gate

- Persistent Discover generations are derived evidence; source/Git/docs/contracts remain authoritative. Disable persistence through strict JSON settings or revert the bounded 084 commit to roll back behavior.
- Corrupt/stale generations and Serena safety artifacts remain recoverable; no permanent-deletion cleanup is authorized.
- 040 stays preserved until this 084 metadata/implementation commit is merged and integrated `main` is verified.
- After integration, run governed cleanup for 084 and then the absorbed 040 worktree/branch; never force-delete either branch.
