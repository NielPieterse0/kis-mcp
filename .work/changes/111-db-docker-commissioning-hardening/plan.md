# DB/Docker Commissioning Hardening Implementation Plan

**Goal:** Make current live provider behavior match the KIS public surface and make commissioning report provider exit status correctly.

**Architecture:** Keep both third-party installations untouched and exactly pinned. Adjust only KIS exposure of the one live-broken Docker Hub operation and the PowerShell wrapper's treatment of stderr.

**Tech Stack:** Python/FastMCP, PowerShell, pytest, existing KIS change workflow and verifier.

## Global constraints

- Stay inside `scope.json`.
- Preserve HR-001/HR-002/HR-003 unchanged.
- Add/adjust the behavior test before implementation.
- Do not update provider revisions or third-party installed bytes.

### Task 1: Capture failing behavior

- Modify `tests/providers/test_dbhub_dockerhub_integration.py` to require the six verified Docker Hub public tools and require `search` to be excluded.
- Run the focused test and record the expected red result against current code.

### Task 2: Implement bounded repair

- Remove only `search` from `PUBLIC_TOOLS`.
- Change commissioning stderr replay from terminating error output to diagnostic host output.
- Run focused tests and live commissioning.

### Task 3: Reconcile current truth and close

- Update `SPEC.md` and `docs/OPERATIONS.md` with commissioned status, exact usable Docker tool set, and residual `search`/dependency risk.
- Run change check, canonical verifier, review, commit, PR/merge, restart both surfaces, verify mounted status, and clean up the worktree.
