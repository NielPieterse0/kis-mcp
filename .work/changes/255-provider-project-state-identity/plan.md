# Provider Project State Identity Implementation Plan

**Goal:** Canonicalize correctness-sensitive provider/project integration state without fragmenting globally safe provider authority.

**Architecture:** Reuse `StateNamespaceResolver`. Classify DBHub commissioning as durable evidence, DBHub generated TOML and Serena project-data identity as reconstructible cache, and retain explicitly global provider state unchanged. Compatibility reads validate exact legacy identity before canonical recovery and never delete legacy evidence.

**Tech Stack:** Python 3.13, FastMCP 4, PowerShell, pytest, Ruff, governed KIS change workflow.

## Global constraints
- Stay inside `scope.json`.
- Preserve provider installation/auth/config/global-cache authority.
- Never silently trust identity-ambiguous legacy provider state.
- Preserve current provider readiness, startup, and tool contracts.

### Task 1: Provider state inventory and classification
- [x] Classify DBHub commissioning/runtime state and Serena project-data identity.
- [x] Record explicit global exemptions, including Docker Hub commissioning.

### Task 2: DBHub canonical state
- [x] Route commissioning evidence to canonical durable-evidence ownership.
- [x] Route generated runtime TOML to source-aware reconstructible-cache ownership.
- [x] Recover only exact legacy commissioning evidence while retaining the legacy file.

### Task 3: Serena canonical identity
- [x] Add registered project/source identity through the canonical resolver.
- [x] Preserve upstream provider cache layout while binding reuse to canonical identity.
- [x] Recover exact legacy root markers; reject unmarked, malformed, mismatched, or ambiguous state without deletion.
### Task 4: Regression and governed closeout
- [x] Prove cross-source isolation, idempotency, legacy recovery, and ambiguity rejection.
- [ ] Run governed scope/verification checks and specialist review.
- [ ] Publish exact commit and pass exact-head GitHub Actions.
- [ ] Merge, commission current revision, complete #556/#548 as eligible, and clean Change 255.
