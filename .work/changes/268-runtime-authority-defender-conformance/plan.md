# Runtime Authority Defender Conformance Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Complete the `kis-mcp` slice of #541 without duplicating commodity-owned remediation.

**Architecture:** Keep repository/runtime location separate from Windows execution trust. Resolve a shared signed system CPython through a machine-readable authority contract, require explicit no-managed-Python uv construction, preserve replaced generated environments through quarantine, and treat Node/native helpers as separate trust layers.

**Tech Stack:** PowerShell, Python/pytest, uv, Windows Authenticode, Windows Code Integrity Operational log, KIS provider/runtime operations.

## Global constraints

- Stay inside `scope.json` for repository writes.
- Do not weaken Defender/SAC or infer trust from `C:\Projects` location.
- Do not copy/relocate a binary as trust remediation.
- Keep the live running KIS environment stable until a separate candidate proves the new construction path.
- Preserve commodity remediation as external to this change.

### Task 1: Establish runtime authority

- [x] Inventory Python, uv, Node, KIS venv, Serena venv, and native helpers.
- [x] Add machine-readable host-runtime ownership/signature policy.
- [x] Add reusable PowerShell resolution/signature validation.

### Task 2: Correct environment construction

- [x] Bind KIS bootstrap to the verified system CPython with `--no-managed-python`.
- [x] Quarantine incompatible generated KIS environments before replacement.
- [x] Bind Serena acquisition/venv construction to the same verified host and persist provenance.

### Task 3: Prove the candidate and trust chain

- [x] Build a separate Python 3.11 candidate from the locked dependency graph.
- [x] Run focused runtime/startup/provider tests from the candidate.
- [x] Inventory Python native artifacts and Node `.node` helpers separately.
- [x] Correlate fresh Code Integrity 3033/3077 events for the workload window.
- [x] Run final change governance, review, and affected verification on the final tree.

### Task 4: Deliver and commission

- [ ] Commit and publish the exact reviewed tree.
- [ ] Create the PR and require exact-head GitHub Actions success.
- [ ] Merge through the governed KIS path, refresh `main`, and perform post-land runtime commissioning.
- [ ] Rebuild/restart live KIS from the landed runtime authority when safe, then verify exact runtime provenance and fresh Code Integrity evidence.
- [ ] Reconcile Work/documentation, close #541 only if its remaining cohort obligations are already satisfied or explicitly transferred, and clean Change 268.
