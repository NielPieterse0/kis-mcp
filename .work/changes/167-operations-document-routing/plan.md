# Operations Document Routing Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Reduce default operator-document context without losing or weakening operational guidance.

**Architecture:** Keep `docs/OPERATIONS.md` as the canonical operator index and delegate detailed procedures to a small `docs/operations/` runbook set. `AGENTS.md` names that subtree as subordinate operator authority. Existing scripts/settings/tests remain the executable source for machine facts.

**Tech Stack:** Markdown, PowerShell, Python/pytest repository checks, Git/KIS governed change workflow.

## Global constraints

- Stay inside `scope.json`.
- Documentation-only: no executable or test modifications.
- Preserve authority order, HR-001/2/3 semantics, tested commands, and recovery guidance.
- Preserve substantive base content; prefer movement over rewriting.
- Root Operations is an index, not a second copy of every runbook.
- PR exact-head verification remains the canonical full repository gate.

---

### Task 1: Establish runbook boundaries

**Files:** `docs/OPERATIONS.md`, `docs/operations/*.md`

- [x] Inventory every legacy H2/H3 section and assign it to one operator runbook.
- [x] Define runbooks for setup, configuration, runtime, providers, review agent, work/discover, remote ChatGPT, verification/change workflow, and recovery/troubleshooting.
- [x] Keep root-only authority/index/fast-path material explicitly identified.

### Task 2: Build the scoped runbooks

**Files:** `docs/operations/setup.md`, `docs/operations/configuration.md`, `docs/operations/runtime.md`, `docs/operations/providers.md`, `docs/operations/review-agent.md`, `docs/operations/work-discover.md`, `docs/operations/chatgpt-remote.md`, `docs/operations/verification-changes.md`, `docs/operations/recovery-troubleshooting.md`

- [x] Preserve each assigned section's operator commands, prerequisites, validation, recovery, and troubleshooting content.
- [x] Remove duplicated current architecture, public-contract detail, machine-owned values, volatile inventories/status, and historical completion claims; route them to `SPEC.md`, settings/contracts/source/tests, or historical evidence as appropriate.
- [x] Adjust relative links for the new directory depth and add an authority/back-link note to each runbook.
- [x] Verify every legacy H2/H3 operator heading is accounted for; all 28 remain. Procedure audits also cover script references, executable command lines, and troubleshooting identifiers with only the documented internal-script exclusion and settings-resolved secret-command replacement.

### Task 3: Replace the root with a routing index

**Files:** `docs/OPERATIONS.md`, `AGENTS.md`

- [x] Keep authority boundary, prerequisites, task-to-runbook index, common startup/verification/change commands, and tested dual-instance invariants in the root.
- [x] Update `AGENTS.md` operator routing and canonical-owner wording to include `docs/operations/**` as subordinate runbooks.
- [x] Remove duplicated detailed procedures from the root.

### Task 4: Review and verify

- [x] Run link and legacy-section/procedure preservation audits.
- [x] Run focused tests that inspect `docs/OPERATIONS.md` plus repository-scope/governance checks.
- [x] Run `git diff --check` and `pwsh -File scripts/change-workflow.ps1 check`.
- [x] Run documentation and architecture specialist reviews on exact staged partitions plus deterministic whole-set audits because the aggregate review package exceeds the reviewer evidence budget.
- [x] Freeze the reviewed source for publication; PR exact-head Canonical Verification owns the full repository gate and merge/cleanup receipts remain external evidence.