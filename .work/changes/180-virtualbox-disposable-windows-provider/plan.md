# VirtualBox Disposable Windows Provider Implementation Plan

> Execute task-by-task; `scope.json` remains authoritative. The operator's explicit implementation instruction follows the approved VirtualBox-first issue #324 decision and authorizes this bounded plan.

**Goal:** Add a fail-closed VirtualBox disposable Windows provider while preserving the existing provider-neutral execution contract, local-process backend, and Hyper-V backend.

**Architecture:** Implement a sibling `VirtualBoxDisposableExecutionProvider` that owns only VirtualBox lifecycle mechanics. Keep execution/verification contracts provider-neutral. Generalize the internal proof service from a Hyper-V concrete type to `ExecutionProvider`. Use an isolated KIS-owned `VBOX_USER_HOME`, a versioned Windows template snapshot, exact Git archive injection through Guest Additions, pre-start isolation, bounded evidence, and recoverable quarantine.

**Tech stack:** Python 3.13, PowerShell 7, Oracle `VBoxManage` 7.x command surface, JSON settings/schema, existing KIS process runner and execution contracts.

## Global constraints

- Stay inside `scope.json`; `.github/workflows/**` remains excluded.
- Add failing tests before behavior changes.
- No new Work hard rule; HR-001/HR-002/HR-003 remain complete.
- Do not mutate Hyper-V/VBS/Memory Integrity, Defender, or Smart App Control.
- Never place a guest password value in tracked config, receipts, diagnostics, or generated command text.
- Do not use `VBoxManage unregistervm --delete` or filesystem deletion for normal retirement.

### Task 1 — settings and schema

**Files:** `tests/execution/test_settings.py`, `src/kis_mcp/execution/settings.py`, `contracts/execution/settings.schema.json`, `settings/execution-runners.settings.json`

- [ ] Add failing tests for strict VirtualBox settings, KIS state/home/password-file boundaries, and disabled repository profile.- [ ] Implement `VirtualBoxProfileSettings`, profile parsing, and schema branch.
- [ ] Add disabled `windows-virtualbox-proof` with KIS-owned state and `VBOX_USER_HOME`.
- [ ] Run focused settings/schema tests.

### Task 2 — VirtualBox lifecycle provider

**Files:** `tests/execution/test_virtualbox_provider.py`, `src/kis_mcp/execution/virtualbox.py`, `src/kis_mcp/execution/__init__.py`

- [ ] Add failing provider tests for readiness, lifecycle ordering, pre-start isolation, exact-source identity, repeat attempts, bounded receipts, missing guest result, and quarantine behavior.
- [ ] Implement `VBoxManage` command wrappers that force the configured KIS `VBOX_USER_HOME` for every command.
- [ ] Verify template config belongs to KIS state and configured shared folders are absent before cloning.
- [ ] Clone exact snapshot into per-attempt base folder, harden VM settings before start, wait for Guest Additions userland, copy exact archive, and execute the declared command.
- [ ] Retire by power-off + isolation + autostart-off + quarantine rename; retain state and evidence.
- [ ] Run focused provider tests.

### Task 3 — provider-neutral proof adapter

**Files:** `tests/workflows/verification/test_disposable_proof.py`, `src/kis_mcp/workflows/verification/proof.py`

- [ ] Add a failing VirtualBox proof test using the same declared-verification adapter.
- [ ] Replace the concrete Hyper-V provider type requirement with the execution-provider protocol plus exact backend/profile identity matching.
- [ ] Preserve existing Hyper-V proof behavior.
- [ ] Run focused proof tests.

### Task 4 — current/target documentation and operator boundary

**Files:** `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `docs/operations/virtualbox-windows-execution.md`

- [ ] Reconcile current implementation truth: VirtualBox provider exists but remains disabled until host/template commissioning.
- [ ] Update target execution-substrate wording from Hyper-V-only to provider-neutral VirtualBox-first with Hyper-V retained.
- [ ] Add the bounded operator runbook for manual host prerequisite installation, KIS-owned VirtualBox home/template setup, readiness/proof execution, hypervisor/VBS observation, and issue #324 real-work commissioning gates.
### Task 5 — review, verification, and handoff

- [ ] Run focused execution and verification suites plus contract-schema tests.
- [ ] Run architecture and safety/security reviews on the final bounded diff; resolve blocking findings.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check` and `git diff --check`.
- [ ] Run applicable canonical repository verification through the current KIS-local authority.
- [ ] Probe this host for `VBoxManage`; if absent, record live commissioning as blocked without claiming a live VM proof.
- [ ] Record closeout evidence, remaining host prerequisite, and issue #324 commissioning programme.

## Traceability

- REQ-001/009/011 → Tasks 2–3 → provider/proof + regression tests.
- REQ-002/003/004/005/006/007/008 → Tasks 1–2 → settings + provider failure/lifecycle tests.
- REQ-010 → Task 1 → repository settings/schema tests.
- REQ-012 → Task 4/5 → runbook + closeout evidence; commissioning remains separate until real workloads run.