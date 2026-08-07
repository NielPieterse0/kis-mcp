# Instance Startup Lifecycle Hardening Implementation Plan

> **For agentic workers:** Execute inline in this isolated worktree with TDD, review, verification, and governed closeout.

**Goal:** Make `start-chatgpt.ps1` reclaim only stale state for the selected instance, preserve the peer instance, and prove ownership before readiness.

**Architecture:** Add a focused PowerShell lifecycle module that owns process identity, selected-instance stale cleanup, endpoint ownership verification, canonical transient cleanup, and `current.json`. Keep `start-chatgpt.ps1` as orchestration: resolve one instance, invoke lifecycle preflight, start owned processes, verify the selected endpoint, persist current state, and mark final lifecycle state during shutdown or startup failure.

**Tech Stack:** PowerShell 7, Windows CIM/NetTCPConnection, Python pytest, existing KIS quarantine/state paths.

## Global Constraints

- Stay inside `scope.json`.
- Operate only on the selected `$Remote` instance; never enumerate or clean the peer by configuration identity.
- Never kill an unrelated process merely because it owns the selected port.
- No permanent deletion; repository transients move to recoverable quarantine.
- Preserve canonical external Python at `C:\Projects\.kis-mcp\python-env`.
- Do not change policy or work-management implementation in slice 058.

---

### Task 1: Selected-instance identity and stale cleanup
- [x] Add failing tests for exact operation/development command-line identity and peer rejection.
- [x] Implement `scripts/startup-instance-lifecycle.ps1` identity/process-tree helpers.
- [x] Add selected-instance server/tunnel stale cleanup with exact executable, command-line, instance, profile, and endpoint evidence.
- [x] Cover empty process sets and root/child selection.

### Task 2: Ownership state and endpoint proof
- [x] Add failing tests for `current.json`, selected listener ancestry, and full-tree shutdown.
- [x] Implement atomic current-state replacement and post-start listener ownership verification.
- [x] Record truthful `restarting`, `preflight_failed`, `startup_failed`, `ready`, and `stopped` lifecycle states.
- [x] Integrate lifecycle preflight before secret unlock and ownership proof before readiness output.

### Task 3: Canonical transient cleanup and regression coverage
- [x] Add tests for recoverable `.venv` / `.pytest_cache` handling and canonical Python enforcement.
- [x] Implement startup-preflight quarantine of those repository-root transients.
- [x] Preserve the peer-instance invariant and remove the old parent-only `Kill()` cleanup path.
- [x] Run focused startup/tunnel tests, scope check, and canonical repository verification.

### Task 4: Review, documentation, and commissioning handoff
- [x] Reconcile `docs/OPERATIONS.md` after change 058 released its unused claim.
- [x] Record direct review and the unavailable optional agent-review backend.
- [x] Capture pre-commissioning listener evidence: operation on 8010, development 8011 free.
- [x] Classify credential-gated live `kis-dev` startup from merged `main` as the immediate post-merge operational commissioning check rather than an unattended implementation gate.
