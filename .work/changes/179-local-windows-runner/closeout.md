# Closeout: Local Windows Runner

## Implemented scope

- `local-process` is the primary Actions-independent Windows execution backend; VirtualBox/Hyper-V remain optional higher-isolation proof providers.
- Canonical commit verification materializes a unique detached exact-SHA worktree under KIS state, rechecks clean HEAD/tree, and runs through a KIS-owned Windows Job Object with kill-on-close containment.
- Exact runs retain per-run state, bounded stdout/stderr, immutable receipt plus SHA-256 sidecar, source revision/tree/fingerprint, runner identity, and evidence reference.
- Timeout, cancellation, parent loss, containment failure, and stale nonterminal state fail closed; stale prior-owner runs are cancellation-reconciled and never promoted to authority.
- `run_verification(exact_revision=...)` requires a full lowercase 40-character commit SHA. Commit-source `execute_change_workflow` propagates that SHA and rejects verification results without matching canonical receipt identity.
- Mutable focused verification remains compatible. Schema-v1 local runner profiles without the new `local` block retain documented defaults; explicit local settings override them.

## Verification

- Focused execution/verification/change-execution/completion suites: passed.
- Windows Job Object descendant timeout and parent-loss tests: passed.
- Exact detached-worktree/receipt integration test: passed.
- Governed scope check and `git diff --check`: passed.
- Canonical `pwsh -File scripts/verify.ps1`: passed on implementation/docs heads with repository line-ending, configuration, interpreter, dependency, syntax, governance, and full pytest checks green; two expected platform skips only.

## Commissioning

`commission_local_runner.py` exercised six exact committed sources with `github_actions_calls: 0`; `commissioning.json` records the durable evidence.

- Concurrent pair 1: critical coordinator slice #251 + registered product repo `doc-solution`; both passed in distinct run/workspace namespaces.
- Concurrent pair 2: critical coordinator slice #252 + current Large #338 implementation; both passed in distinct run/workspace namespaces.
- Small: change 122 exact commit passed.
- Medium: change 121 exact commit passed.
- Large: #338 exact commit passed.
- Registered product repo: clean `doc-solution` exact HEAD passed its 327-test unittest suite under its required Python 3.11.9 runtime. The first attempt correctly failed because the KIS Python 3.13.7 runtime did not match that repo's committed frontend-assurance runtime contract; rerunning with the repo-required installed 3.11.9 runtime passed.
- All six successful runs returned `authoritative=true`, unique run directories/workspaces, exact requested=resolved revisions, and receipt hashes verified against receipt bytes.

Successful receipt SHA-256 values:

- #251: `1bb740cb4e32b8e260c554be42ea5f3616c55db1977d5b197e20f849144bdaba`
- #252: `c010a0352528bac152021904da27d4ac204c7d343333ca2f7506090d9f8277a2`
- Large #338: `094f6ca158e0b0d232aa945e3abd399601550937e952151f73b9f7c18afdc4f2`
- Medium 121: `a5ee08a4a36121c12e798de4f4ee41a24bf12c9f39c514619f388d87472d3769`
- Product `doc-solution`: `c32d09f8ee7f40e6c5fba9fa56ab09c0c1bf1117a85e71167daa4c665dad13bd`
- Small 122: `90dff98e4e45df5bb0c55be0232d3f7899b32f5a1e706bfe8b8f6520004eb383`

## Review

Required review types from the large-change risk profile are code quality, safety/security, architecture, and API contracts.

- Initial code-quality review found a real stale-owner PID reuse risk; fixed by replacing PID-only ownership with a per-process random owner token and regression coverage.
- Safety/security reviews found no evidence-backed vulnerability after the fix.
- Architecture/API reviews raised compatibility concerns around new evidence/settings fields; new execution evidence remains additive/optional, legacy schema-v1 local profiles retain defaults, and exact SHA strictness is intentional and documented.
- Several whole-range NVIDIA reviews failed with provider 503/timeouts and the Codex CLI fallback failed in its current quota/process state. Those failures are not counted as review approval.
- Final manual exact-diff fallback covered base `8cc759d4766c22ca522b1834d8ec0b92954d6bca` through candidate `abce3cd77a5535058052049b8081595444ec382d` across code, contracts, tests, documentation, and commissioning evidence. No additional blocking code-quality, safety/security, architecture, or API-contract finding remained; the final `abce3cd` delta is commissioning/evidence-only.
- The six retained commissioning receipts were independently re-hashed from disk after review and all matched their recorded SHA-256 values; run/workspace namespaces remain unique and `github_actions_calls` remains `0`.

## Recovery and residual state

- Exact-run worktrees and receipts are intentionally retained beneath `C:\Projects\.kis-mcp\execution\local\runs` as recoverable evidence; no automatic permanent deletion is introduced.
- Operator CPU/RAM admission remains explicit; no adaptive resource governor was added.
- Coordinator leases, fencing, reservations, and serialized integration are unchanged.
- GitHub Actions remain available only as optional diagnostics and are not required by this implementation.

## Git and landing

- Change branch: `change/179-local-windows-runner`.
- Base: `8cc759d4766c22ca522b1834d8ec0b92954d6bca`.
- Publication/PR/exact-PR-head receipt/merge/tracking refresh/cleanup: pending final current-head review and verification.
