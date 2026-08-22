# Change Specification: Issue Close Readback and kis-dev Post-Land Restart

- **Change ID**: `231-issue-close-readback-confirmation`
- **Status**: Active
- **Risk Profile**: external-action, deployment, public-contract, architecture-boundary
- **Development Level**: Medium

## Outcome

Commissioning closeout must confirm source issue closure from authoritative provider read-back. Any governed `kis-mcp` pull-request landing on `main` must also schedule a safe refresh of primary `main` followed by replacement of `kis-dev` only.

## Requirements

- **REQ-001**: Treat successful `github_issue_write` as mutation acknowledgement only; confirm the exact issue number and `state=closed` with `github_issue_read` before terminal commissioning success.
- **REQ-002**: Preserve resumable phase behavior; a resumed `work_completed` execution must not repeat passed probes or Work completion.
- **REQ-003**: Direct exact-head merge and merge-queue landing for project `kis-mcp` on `main` must emit the same post-land event to one shared runtime-composed dispatcher after verified landing.
- **REQ-004**: The dispatcher must target only `kis-dev` / `development`; it must contain no operation-instance selection or peer-instance cleanup path, and generated-state ownership must be injected from validated runtime configuration rather than re-read from the mutable checkout.
- **REQ-005**: Before restart, the worker must require clean primary `main`, fetch verified `origin/main`, fast-forward only, and prove the required merge/base/head reference is contained in the synchronized local `main`.
- **REQ-006**: Replacement startup must reuse existing selected-instance identity/reclaim logic and run detached from the old server process tree.
- **REQ-007**: Failure to synchronize or restart must fail closed with retained bounded evidence; it must never reset/diverge local Git state or touch `kis-op`.
- **REQ-008**: Non-`kis-mcp` repositories and non-`main` landing paths must not schedule a restart.

## Acceptance

1. A narrow `{id,url}` close-write response reaches terminal success only after authoritative issue read-back confirms the exact issue is closed.
2. An open or mismatched read-back is rejected as unconfirmed closure.
3. Both KIS landing mechanisms emit to the shared post-land dispatcher for `kis-mcp/main`; other projects do not schedule a restart.
4. The restart worker uses only fast-forward synchronization and then invokes `start-chatgpt.ps1 kis-dev`.
5. Regression tests execute the isolated worker path and prove its actual restart target is exactly `kis-dev`; source-level checks remain supplementary and the detached CIM scheduler boundary is covered separately.
6. Focused commissioning, landing, startup-script, scope, and repository verification gates pass.

## Recovery and boundaries

- The GitHub merge itself remains authoritative once provider verification reports landed; restart scheduling is a post-land side effect with its own receipt.
- A dirty/diverged primary checkout blocks synchronization and restart rather than rewriting local work.
- Existing selected-instance startup code owns safe `kis-dev` reclaim and unrelated-port refusal.
- No `kis-op` runtime, settings record, port, profile, tunnel, state file, process, or lifecycle operation is in scope.
