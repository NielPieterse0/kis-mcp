# Tasks: State Ownership Namespace

- [x] Confirm authority, current `main`, issue #278 scope, #272/#277 decision, and #265 handoff.
- [x] Create isolated governed change `163-state-ownership-namespace` from verified current `main`.
- [x] Record specification and implementation plan.
- [x] Add failing #278 contract/resolver tests and machine-readable contract/schema.
- [x] Implement `kis_mcp.state` ownership classes, source identities, resolver, and bounded diagnostics.
- [x] Document the state-ownership contract and explicit no-migration boundary.
- [x] Run focused tests and schema validation: 65/65 state + governance tests green; `git diff --check` clean.
- [x] Run `pwsh -File scripts/change-workflow.ps1 check` on the pre-publication tree; scope check passed.
- [ ] Observe canonical repository verification on the exact pull-request head in GitHub Actions.
- [ ] Complete code-quality, architecture, API-contract, test-quality, and documentation review gates on one exact source.
- [ ] Commit and prepare exact-head pull request.
- [ ] Observe exact-head CI, merge through governed workflow, reconcile #278, and clean only this worktree.
