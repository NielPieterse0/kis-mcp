# Implementation Plan: Issue Close Readback and kis-dev Post-Land Restart

**Goal:** Correct commissioning close confirmation and make landed `kis-mcp/main` code automatically become the live `kis-dev` runtime without disturbing `kis-op`.

**Architecture:** Keep provider truth in the commissioning runner. Add one KIS-specific post-land scheduler shared by direct merge and merge-queue landing. The scheduler uses Windows CIM to detach a bounded PowerShell worker from the current server tree. The worker safely fast-forwards primary `main`, proves the landed SHA, then reuses the existing `start-chatgpt.ps1 kis-dev` selected-instance lifecycle.

## Constraints

- Test first for each behavioral slice.
- No `kis-op` invocation, inspection, stop, restart, port access, profile access, or state mutation.
- No reset, force checkout, branch deletion, or non-fast-forward local update.
- Post-land worker evidence remains beneath KIS generated state, not repository authority.
- Existing exact-head landing and selected-instance identity checks remain authoritative.

### Task 1 — Commissioning close read-back

- Add regression coverage for provider write response `{id,url}`.
- Require `github_issue_read` after the close write and validate exact number/state.
- Cover mismatched/open read-back failure and resume behavior.

### Task 2 — Safe post-land restart worker

- Add scheduler module and detached PowerShell worker.
- Require project `kis-mcp`, branch `main`, exact landed SHA, clean primary main, verified fetch, and fast-forward-only synchronization.
- Retain success/failure receipt and launch only `start-chatgpt.ps1 kis-dev`.

### Task 3 — Bind both landing mechanisms

- Schedule only after direct PR merge is provider-verified as `MERGED` on `main`.
- Schedule only after merge-queue base advancement returns `landed` on `main`.
- Do not schedule for other registered projects or branches.

### Task 4 — Documentation, review, verification, delivery

- Update the ChatGPT remote runbook with the automatic `kis-dev` post-land lifecycle and fail-closed synchronization conditions.
- Run focused tests and `change-workflow.ps1 check`.
- Run required code-quality, API-contract, architecture, and documentation reviews on the final exact diff; remediate findings.
- Publish, require exact-head CI and Work Management merge-readiness, merge, synchronize local main, and allow the landed hook/new runtime to replace only `kis-dev`.
- Resume commissioning #462 from persisted state and prove terminal success without restarting `kis-op`.
