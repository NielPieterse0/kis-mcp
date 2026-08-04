# Tasks: 008 GitHub MCP Provider

## Lifecycle

- [x] Read repository authority and approved platform concept.
- [x] Inspect active parallel claims and exclude Discover/remote commissioning paths.
- [x] Classify as Complex.
- [x] Create isolated emergency worktree after official registration was blocked by duplicate merged claims.
- [x] Register local scope artifacts before implementation edits.
- [x] Run immediate governance validation; blocked by pre-existing duplicate `004`/`006` records.
- [x] Run clean baseline verification; passed.
- [x] Task 1 — provider settings and schema.
- [x] Task 2 — repository scope middleware.
- [x] Task 3 — registry, server, and health.
- [x] Task 4 — bootstrap, smoke, and operations.
- [ ] Task 5 — final staged review, verification, commit, push, and draft PR.

## Evidence

- Baseline `scripts/verify.ps1`: PASS; existing suite completed with one skip.
- Initial TDD red: full verification failed during collection because the new provider modules did not exist.
- Scope regression red: alternate repository fields and malformed targets failed before the corrective extraction/error normalization change.
- Live commissioning red: the script test failed while `-RequireLive` only invoked `--help`; the replacement now performs a real MCP surface/auth/private-read smoke.
- Focused green: `scripts/smoke-github-mcp.ps1` PASS; 34 tests.
- JSON validation: provider settings and schema PASS.
- Full green: `scripts/verify.ps1` PASS with configuration, interpreter, dependency, syntax, pytest, and exact three-rule verification checks.
- Governance registration/validation: BLOCKED by duplicate `004-live-proxy-commissioning` and `006-provider-state-atomicity` claim copies; no `008` versus current independent provider scope overlap was identified.
- Live readiness: executable absent and token absent; no live GitHub call claim.
