# Git Workflow Tooling

## Purpose

This slice adds local, fixed-shape Git workflow evidence for coding agents working with governed branches and worktrees. It does not replace Git, the GitHub connector, or the repository change workflow.

The commands are implemented by:

```text
scripts/git-workflow.ps1
└── scripts/git-workflow.py
```

All operations are local and read-only. The only mutation change is narrow hardening of the existing governed `cleanup` command.

## Commands

### Structured diff

```powershell
pwsh -NoProfile -File scripts/git-workflow.ps1 diff-summary `
  --base main `
  --head HEAD
```

Optional parameters:

- `--path <repository-relative-path>` limits the comparison.
- `--max-files <positive-int>` bounds returned file records.
- `--max-output-bytes <positive-int>` bounds each Git command output.

The JSON result includes:

- resolved repository, base, head, and merge base;
- commits between merge base and head;
- deterministic file records with status, previous path, similarity, additions, deletions, and binary state;
- aggregate status and line counts;
- explicit truncation and omission counts.

Refs and paths are validated before Git execution. Option-shaped refs, whitespace, traversal-like refs, and ambiguous paths are rejected structurally. Git stdout and stderr are drained incrementally under one combined byte cap, and each command has a 30-second timeout; large output is never fully buffered before rejection.

### PR readiness

```powershell
pwsh -NoProfile -File scripts/git-workflow.ps1 pr-readiness --base main
```

The command reports:

- branch, governed change ID, head, base, ahead, and behind counts;
- clean or dirty worktree state;
- detached-head state;
- registered scope-check evidence;
- readiness blockers and recommended local actions.

Readiness requires a clean named `change/<id>` branch, at least one commit beyond the base, no base-behind commits, and a passing registered scope check.

This command does not push, create a PR, request review, merge, or delete a remote branch. Those remain explicit GitHub connector operations.

### Cleanup preview

```powershell
pwsh -NoProfile -File scripts/git-workflow.ps1 cleanup-preview
pwsh -NoProfile -File scripts/git-workflow.ps1 cleanup-preview --change-id 045-git-workflow-tooling
```

The command lists managed change worktrees and reports:

- registration and base;
- cleanliness;
- merge ancestry;
- long-path risk;
- cleanup eligibility and exact blockers.

It performs no mutation.

## Recoverable cleanup hardening

The existing command remains authoritative:

```powershell
pwsh -NoProfile -File scripts/change-workflow.ps1 cleanup <change-id>
```

Cleanup still requires:

- the canonical managed worktree;
- a clean working tree;
- exactly one change claim;
- a branch merged into its declared base.

Worktree removal now uses:

```text
git -c core.longpaths=true worktree remove <path>
```

If Git reports failure, cleanup checks registration again:

1. If the branch is still registered as a worktree, cleanup stops. It does not move the directory or delete the branch.
2. If registration is gone and no directory remains, cleanup continues normally.
3. If registration is gone but an intact directory remains, the directory is moved to:

```text
C:\Projects\.backup\<change-id>-worktree-remnant-<UTC timestamp>
```

Only after safe removal or recovery does cleanup delete the local merged branch and prune stale worktree metadata. No force deletion is used.

The cleanup JSON result now includes:

```json
{
  "cleaned": "045-git-workflow-tooling",
  "branch": "change/045-git-workflow-tooling",
  "recovered": false,
  "backup_path": null
}
```

## Boundaries

- No external packages or Git extensions are installed.
- No Tool or Provider package is added.
- No external network access is used by the local commands.
- No remote PR mutation is performed.
- No force push, history rewrite, force branch deletion, or permanent deletion is available.
- Unrelated active worktrees are never cleaned automatically.
