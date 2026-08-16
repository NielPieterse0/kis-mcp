# Closeout: Python Worktree Source Isolation

## Implemented scope

- Added `RepositoryProcessEnvironmentNormalizer` at the generic Desktop Commander process-call boundary for `start_process` and `execute_command`.
- Source-sensitive process identity is derived from the effective shell working directory and nearest registered Git checkout/worktree; `<checkout>/src` becomes the process-local Python source root.
- The selected source root is prepended to process-local `PYTHONPATH` without installing, editing, or otherwise mutating the selected virtualenv.
- Ambiguous multi-worktree commands, explicit `PYTHONPATH` rewrites, unsupported shells, unsafe cmd paths, and source disappearance fail explicitly with `PROCESS_SOURCE_*` structural errors.
- PowerShell environment-provider mutations are resolved by cmdlet argument roles and observed provider-path semantics, including named/positional binding and canonical slash/backslash root forms without false positives for different environment-variable names.
- `run_verification` no longer carries a private `PYTHONPATH` implementation; verification consumes the same generic process boundary.
- No HR policy, provider tool schema, persistent KIS state, or other lane-owned paths were changed.

## Validation evidence

- TDD repeatedly reproduced the source leak and each reviewer-discovered fail-closed/parser gap before production fixes were applied.
- Final focused regression: **42 tests passed** across `tests/test_process_environment.py` and `tests/workflows/verification/test_verification_execution.py` on the final implementation state.
- The real editable-path regression creates a shared external venv whose `.pth` points at root `main/src`; the unnormalized worktree process imports `root-main`, while the normalized process imports the selected worktree package without changing that venv.
- Live PowerShell probes verified the exact Env-provider separator behavior used by the parser, including the distinction between canonical root forms and separator text that becomes part of a different environment-variable name.
- `py_compile` passed for all changed production/test Python modules.
- `git diff --check` passed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check` passed with all changed paths inside the declared #265 claim.
- Ruff is not installed in the locked Python environment; no alternate environment was substituted and no Ruff pass is claimed.
- Per repository policy, the canonical full repository verifier is not repeated locally on the PR path; exact-head GitHub Actions remains the merge gate.

## Review

- Iterative exact-commit Codex reviews found concrete gaps in PowerShell provider mutation detection, cmd source-disappearance handling, provider-path spellings, and PowerShell positional/named parameter binding. Each valid finding was reproduced and fixed with regression coverage.
- Final semantic hardening commit `f20f171af5e5546c215b39e006a2b9113f006a7b` received an independent Codex code-quality review with **zero findings**.
- Final full-range architecture review on fingerprint `c950bbcab309fee0536759e90cde6579a545c05a58533c6f8d8d07c99409cfd6` returned informational confirmations only; no actionable findings.
- Final full-range API-contract review on the same fingerprint returned **zero findings**.
- One whole-range NVIDIA code-quality attempt exhausted its review deadline and produced no verdict; it is retained as backend-availability evidence, not counted as approval or a finding.

## Git and delivery

- Branch: `change/160-python-worktree-source-isolation`
- Worktree: `.work/worktrees/160-python-worktree-source-isolation`
- Declared base: `785840c7b496e505b7b6ee6766e7594f14d632ce`
- Final local implementation head before closeout metadata: `f20f171af5e5546c215b39e006a2b9113f006a7b`.
- Pull request: #285. Its review branch must be reconciled to the final closeout commit and pass canonical exact-head GitHub Actions before merge.
- Post-merge cleanup uses the schema-v4 governed cleanup path; no second repository commit is required solely to rewrite lifecycle status.

## Residual items

- Explicit dependency synchronization can still repoint the shared canonical virtualenv; #265 removes source-correctness dependence on that mutable editable pointer but does not redesign dependency synchronization.
- #278 remains authority for durable state ownership. The recorded handoff is: source-sensitive execution identity is the nearest registered checkout/worktree selected from effective process cwd; binding is ephemeral/process-local and ambiguity fails closed.
