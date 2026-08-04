# P1 Boundary Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for every behavior change and superpowers:verification-before-completion before any completion claim.

**Goal:** Close the six approved P1 findings with narrow, test-backed changes at the existing Work, GitHub provider, and Discover boundaries.

**Architecture:** Keep `command_intent.py` as the provider-neutral command-effect entry point but replace its Git and shell assumptions with explicit parsed invocation state. Add process lifecycle observation through the existing resolver/middleware seam, harden GitHub search grammar conservatively, and validate the complete statically discoverable Git metadata graph before Discover invokes Git.

**Tech Stack:** Python 3.11+, FastMCP middleware, pytest, Windows paths, Git local configuration files, PowerShell verification scripts.

## Global Constraints

- Enforce exactly HR-001, HR-002, and HR-003; add no fourth restriction.
- Unknown or unresolved effects remain allowed.
- Write only inside `C:\Projects`; no permanent deletion.
- Do not modify active Skills, Startup Hardening, Provider Runtime Composition, Supabase, server composition, policy, settings, or quarantine surfaces.
- Use no new runtime dependency.

---

### Task 1: Register and baseline the isolated slice

**Requirements:** Scope discipline and acceptance evidence.

**Files:**
- Create: `.work/changes/015-p1-boundary-hardening/{scope.json,spec.md,plan.md,tasks.md,closeout.md}`

- [x] Create isolated branch and worktree from clean `main`.
- [x] Record exclusive owned and excluded paths.
- [x] Run full baseline verification and record the result.
- [x] Run the global claim validator and preserve the pre-existing recursive duplicate failure.

### Task 2: Git invocation and network target resolution

**Requirements:** R1, R4.

**Files:**
- Modify: `src/kis_mcp/command_intent.py`
- Test: `tests/test_desktop_commander.py`

- [x] Add failing tests for `git -C`, `--git-dir`, `--work-tree`, repeated `-C`, forced `clean`, and effective metadata write paths.
- [x] Add failing tests for `pushurl`, `--repo`, branch push precedence, multiple remotes, and local includes.
- [x] Run the targeted tests and confirm expected failures.
- [x] Implement a parsed Git invocation record and operation-specific repository/URL resolution.
- [x] Run targeted and existing command-intent tests to green.

### Task 3: Shell parsing and stateful interactive processes

**Requirements:** R2, R3.

**Files:**
- Modify: `src/kis_mcp/command_intent.py`
- Modify: `src/kis_mcp/desktop_commander.py`
- Modify: `src/kis_mcp/middleware.py`
- Modify if required: `src/kis_mcp/contracts.py`
- Test: `tests/test_desktop_commander.py`
- Test: `tests/test_middleware.py`

- [x] Add failing tests for CMD single `&`, grouping, PowerShell invocation/script blocks, and escaped separators.
- [x] Add failing tests for sequential `cd`, `Set-Location`, `pushd`, and `popd` followed by relative write/move/Git/delete operations.
- [x] Add middleware lifecycle tests proving successful `start_process` result registration and `interact_with_process` state reuse/reset.
- [x] Run targeted tests and confirm expected failures.
- [x] Implement shell-dialect splitting and sequential directory state.
- [x] Implement bounded process-state observation after successful provider calls.
- [x] Run targeted and existing Work/middleware tests to green.

### Task 4: GitHub repository search scope

**Requirements:** R5.

**Files:**
- Modify: `src/kis_mcp/providers/github/scope.py`
- Test: `tests/providers/github/test_scope.py`

- [x] Add failing tests for `OR`, `NOT`, parentheses, quoted qualifiers, multiple repo qualifiers, and conflicting organization/user/owner qualifiers.
- [x] Run tests and confirm expected failures.
- [x] Implement a bounded search grammar that proves one approved repository scope while permitting subordinate grouping, filters, and safe exclusions.
- [x] Run the GitHub scope suite to green.

### Task 5: Discover Git metadata graph validation

**Requirements:** R6.

**Files:**
- Modify: `src/kis_mcp/discover/git_reader.py`
- Test: `tests/discover/test_git_reader.py`
- Test: `tests/discover/test_git_hardening.py`

- [x] Add failing tests for outside-boundary `commondir`, alternates, index, config include, and unsafe nested metadata paths.
- [x] Prove no Git subprocess runs after metadata validation rejects a repository.
- [x] Run tests and confirm expected failures.
- [x] Implement active metadata-path resolution and validation before the first Git command while ignoring passive references that are not traversed.
- [x] Run Discover Git tests to green.

### Task 6: Integrated review and verification

**Requirements:** R1–R6 and acceptance evidence.

**Files:**
- Update: `.work/changes/015-p1-boundary-hardening/{tasks.md,closeout.md}`

- [x] Run targeted Work, middleware, GitHub scope, and Discover Git suites.
- [x] Review the diff against the specification, negative proof standard, and active-slice exclusions.
- [x] Fix every Critical or Important finding and rerun affected checks.
- [x] Run `pwsh -File scripts/change-workflow.ps1 check` from the change worktree.
- [x] Run full `pwsh -File scripts/verify.ps1` on the final tree.
- [x] Record exact commands, outcomes, residual risks, and rollback.
- [x] Prepare the verified branch for commit, push, and pull-request creation against `main`.
