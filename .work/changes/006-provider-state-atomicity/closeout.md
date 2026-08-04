# Closeout: Provider State Atomicity

## Implemented scope

- Added `src/kis_mcp/provider_state_atomic.cjs`, a narrowly targeted Node preload adapter.
- The adapter intercepts only `fs/promises.writeFile` calls whose resolved path exactly matches the provider state path supplied through `KIS_MCP_PROVIDER_STATE_FILE`.
- Target writes are redirected to a unique same-directory temporary file and completed with rename over the target.
- Non-target writes retain their original path, data, options, and underlying implementation.
- Added `src/kis_mcp/provider_lifecycle.py` to preload the bundled adapter and inject the runtime-configured state path without mutating launch inputs.
- Updated `src/kis_mcp/server.py` only to use the prepared provider arguments and environment.
- Desktop Commander installation contents, settings, policy, provider schemas, exposed tools, and PR #3 commissioning files were not changed.

## Root-cause evidence

- The unchanged PR #3 commissioning harness reproduced `PROVIDER_STATE_INTEGRITY` with a zero-byte `config.json`.
- Desktop Commander `0.2.46` records tool usage through `setValueNonBlocking`, which schedules an asynchronous `fs/promises.writeFile`.
- MCP stdio shutdown may terminate the Node process after the target has been truncated but before replacement bytes are complete.
- Provider write serialization prevents overlapping writes but does not make an individual replacement interruption-safe.

## Validation evidence

- TDD RED 1: `tests/test_provider_lifecycle.py` failed because `provider_state_atomic.cjs` did not exist.
- TDD GREEN 1: adapter ordering and non-target passthrough test passed.
- TDD RED 2: launch-shaping test failed because `provider_lifecycle.py` did not exist.
- TDD GREEN 2: both lifecycle tests passed.
- Focused checks: 21 provider lifecycle, readiness, and provider-contract tests passed.
- Live commissioning: the unchanged PR #3 harness ran against the 006 source tree and passed all nine stages.
- Repetition: three additional complete live commissioning runs passed all nine stages.
- Provider state: the valid target remained intact and passed JSON, empty `blockedCommands`, empty `allowedDirectories`, and disabled-telemetry validation without snapshot restoration.
- Package evidence: Node syntax validation passed; an offline wheel built using the repository's locked cache and contained `kis_mcp/provider_state_atomic.cjs`.
- Repository verification: `pwsh -File scripts/verify.ps1` passed with 144 tests and 19 Python source files parsed.
- Diff scope: `pwsh -File scripts/change-workflow.ps1 check` passed with exactly 11 declared paths.
- Whitespace: `git diff --check` passed.
- Static review: 35 Python files analyzed with zero warnings and zero errors.

## Review

- Blocking findings: none.
- Scope correction: normalized `src/kis_mcp/server.py` to repository LF form after detecting a false full-file CRLF diff; the final diff contains only one import and the provider launch preparation block.
- Parallel-work check: `src/kis_mcp/server.py` is explicitly shared with `005-discover-foundation`; 005 currently retains the baseline launch block, so no present content conflict was found. Integration ownership remains recorded in `scope.json`.
- Policy review: no fourth rule, tool block, command restriction, schema restriction, network restriction, approval gate, or machine-specific provider state path was added.

## Recovery and residual behavior

- Repository rollback: revert the branch commit. No installed provider file requires restoration because the provider package is not modified.
- Runtime recovery: the last valid `config.json` remains at the configured target if shutdown interrupts before rename.
- Residual behavior: an interrupted temporary write can leave a uniquely named same-directory `.config.json.<pid>.<uuid>.tmp` file, commonly zero bytes. This is recoverable generated-state residue and does not replace or invalidate the target.
- No automatic permanent cleanup was added because HR-003 prohibits permanent deletion through Work and cleanup is not required to close the corruption defect.

## Git and merge

- Branch: `change/006-provider-state-atomicity`
- Worktree: `.work/worktrees/006-provider-state-atomicity`
- Base: `main`
- Implementation commit: `5eb72a60d9dff4d18904205b74b281d38c667ee3`
- Pull request: `#4` — `https://github.com/NielPieterse0/kis-mcp/pull/4`
- Pull request state: open, draft, and unmerged.
- Merge: not authorized; explicit confirmation is required for the final current PR head.
- Cleanup: deferred until the branch is merged and the primary `main` worktree is clean.

## Residual items

- PR #3 must remain draft until this change is merged into its branch and its own live commissioning command passes on the integrated head.
- Temporary provider-state files may accumulate one per interrupted background save. A separate bounded recovery/quarantine policy can be considered only if accumulation becomes operationally material.
