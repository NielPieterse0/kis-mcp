# Local Windows Runner Implementation Plan

> **For agentic workers:** Execute task-by-task inside the declared worktree and keep scope/evidence current.

**Goal:** Replace mutable/Actions-dependent canonical verification assumptions with exact-source, contained local Windows execution while preserving the Work policy boundary.

**Architecture:** Keep ordinary `run_verification` routing through nested Work process execution. For canonical commit verification, first materialize a unique detached worktree under KIS state, then launch a small KIS worker through the same nested Work process surface. The worker owns a Windows Job Object and captures bounded durable evidence. Exact run state is namespaced per request; stale state is cancellation-only and never authoritative.

**Tech stack:** Python stdlib (`ctypes`, `subprocess`, `hashlib`, `json`), Git worktrees, PowerShell command composition, existing FastMCP/Work runner abstraction, pytest.

## Global constraints

- Stay inside `scope.json`; coordinator internals remain excluded.
- Tests precede or accompany behavior changes; exact-source failures fail closed.
- No global CPU/RAM governor or automatic workload admission.
- Do not bypass FastMCP/Work middleware for repository verification commands.
- Do not permanently delete retained exact-run workspaces during execution.

### Task 1: Contract and settings

- Add local-runner state/timeout settings and schema validation.
- Extend verification evidence with optional exact source/receipt identity while preserving mutable-run compatibility.
- Add failing settings/contract tests first.

### Task 2: Windows containment worker

- Add a stdlib-only worker that creates/configures a kill-on-close Job Object, assigns the verifier child, captures stdout/stderr, and handles timeout/cancel/parent loss.
- Add unit tests plus a Windows integration test proving descendant termination.
### Task 3: Exact-source local execution

- Add per-run state management and stale-run cancellation reconciliation under the configured KIS state root.
- Materialize exact commits into unique detached worktrees through the existing Work runner and verify HEAD/tree before use.
- Execute exact verification through the containment worker and emit the canonical immutable receipt plus digest reference.
- Preserve existing mutable focused verification behavior.

### Task 4: Workflow integration

- Add optional exact revision to `run_verification`.
- Pass commit-source identity from `execute_change_workflow` into each verification call.
- Reject commit-source verification that does not return matching exact-source receipt evidence.
- Regression-test `prepare_reviewable_pull_request`/change-execution exact commit propagation.

### Task 5: Documentation and commissioning

- Update `SPEC.md` and the verification runbook to make local exact execution primary and VirtualBox optional.
- Run focused execution/verification/completion tests and the governed scope check.
- Run canonical repository verification locally with zero GitHub Actions dependency.
- Exercise two concurrent local runs and at least one registered tool-user/product repository where available, recording concrete closeout evidence.
- Complete required specialist reviews, resolve blocking findings, publish PR, exact-head verify, merge, refresh, and safely clean the change worktree.
