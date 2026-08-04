# P1 Boundary Hardening Tasks

| Task | Requirements | Status | Evidence |
|---|---|---|---|
| Register isolated scope and artifacts | Slice governance | Complete | Worktree `015-p1-boundary-hardening`; merged stale claims 005 and 008 closed; `change-workflow.ps1 check` passed |
| Parse Git global options and effective repository paths | R1 | Complete | Regression coverage for `-C`, repeated `-C`, `--git-dir`, `--work-tree`, mutation paths, and `git clean` |
| Track interactive process working-directory state | R2 | Complete | Successful-call state observation, PID-scoped cwd/stack tracking, termination cleanup, and middleware tests |
| Parse CMD and PowerShell control operators | R3 | Complete | CMD `&`/groups, PowerShell invocation/script blocks, escaped separators, and sequential cwd tests pass |
| Resolve operation-specific Git push URLs | R4 | Complete | `pushurl`, `--repo`, branch/default remote, and active local include tests pass |
| Prove GitHub search scope | R5 | Complete | Bounded Boolean parser permits safe filters/grouping/exclusions and separates `unsupported_search_grammar` from `repository_scope_violation` |
| Validate Discover Git metadata graph | R6 | Complete | Active metadata traversal validation passes with harmless remotes, inactive includes, disabled worktree config, and passive unborn alternates preserved |
| Review, scope check, full verification, PR | R1–R6 | Complete | Targeted P1 suite, change-scope check, full locked verification, diff review, and PR preparation completed |
