# Provider Commissioning Evidence Implementation Plan

**Goal:** Preserve historical DBHub/Docker Hub commissioning truth across restarts without conflating it with current-process liveness.

**Architecture:** Add one provider-neutral commissioning evidence helper under `kis_mcp.providers`. It derives its root from runtime `state_root`, computes an exact normalized identity fingerprint, writes/reads one bounded JSON document per provider identity, and never scans or mutates unrelated state. DBHub/Docker Hub readiness consumes only matching evidence; the existing commissioning script records evidence only after a successful live probe.

**Tech Stack:** Python 3.13, JSON, hashlib, pathlib, PowerShell commissioning wrapper, pytest.

## Global constraints

- Stay inside `scope.json`; do not overlap change 125.
- Add failing tests before implementation.
- Preserve provider tool surfaces and current readiness/mount semantics.
- Do not add a new configuration authority; derive state location from existing runtime JSON.

### Task 1: Test durable evidence semantics

- Add helper-level and provider-level tests for missing, valid, malformed, and stale evidence.
- Prove RED against the current hard-coded pending commissioning values.

### Task 2: Implement evidence storage and reconstruction

- Add provider-neutral identity hashing, deterministic path selection, validated read, and idempotent write.
- Integrate DBHub and Docker Hub readiness with exact identity builders.

### Task 3: Record evidence during commissioning

- Update the supervised commissioning probe to persist only successfully verified provider/tool evidence.
- Keep process errors and provider availability behavior unchanged.

### Task 4: Verify and close

- Run focused provider tests, scope checks, review, exact-head CI, live restart commissioning, documentation reconciliation, merge, and cleanup.
