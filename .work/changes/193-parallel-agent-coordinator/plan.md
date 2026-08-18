# Parallel Agent Coordinator Implementation Plan

**Goal:** Reconstruct the proven Change 150 coordinator while removing only the obsolete crisis-era verification authority.

**Architecture:** Restore the historical coordinator contract/runtime/test surface from final retained head `4aae9dd30ad3536a84f5a08f805ae149116773e9`. Keep its authority, planner, worker, and reconciliation boundaries intact. Replace `kis_local_exact_head` with the current repository `github_actions_exact_head` contract and do not add any runner implementation.

**Tech stack:** Python, JSON Schema Draft 2020-12, pytest, Ruff, governed KIS/GitHub lifecycle.

## Global constraints

- Stay inside `scope.json`.
- Historical code is reconstruction evidence, not authority over current repository rules.
- Preserve exact-head GitHub Actions landing assurance.
- No metadata-only commit after the canonical exact-head run.

### Task 1 — Restore retained historical payload

- Restore `contracts/coordinator/**`, coordinator runtime, tests, and module product spec from `4aae9dd…`.
- Confirm no out-of-scope historical files are imported.

### Task 2 — Replace obsolete verification authority

- Update the verification-requirements contract/runtime/tests/spec to `github_actions_exact_head`.
- Add a regression assertion that `kis_local_exact_head` is absent from the reconstructed coordinator surface.
### Task 3 — Focused verification

- Run the full coordinator test suite.
- Validate every strict coordinator JSON schema against its examples/emitted fixtures where covered.
- Run Ruff on coordinator source/tests and governance scope checks.
- Fix only failures attributable to reconstructed-main compatibility.

### Task 4 — Review before canonical Actions

- Run required code-quality, safety/security, API-contract, and architecture reviews concurrently over the complete base→candidate diff.
- Resolve any source-changing finding and rerun only invalidated focused checks/reviews.
- Freeze one final immutable landing head after reviews are clean.

### Task 5 — Exact-head landing

- Publish/create the PR on the frozen head.
- Run one canonical GitHub Actions verification on that exact SHA.
- Require Work Management merge readiness, merge only that head, align/reconcile, and clean local/remote change state.