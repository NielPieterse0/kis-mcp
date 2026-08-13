# Closeout: Workflow Provider Hardening

## Implemented scope

- Exact-commit verification now composes the target-capable Git change reader, so clean committed changes retain commit/range evidence.
- Verification execution prepends the selected project/worktree `src` directory to the child process `PYTHONPATH` when present, preventing root editable-install leakage.
- Explicit empty specialist review lists remain valid while omitted reviews retain risk-profile defaults; project/path translation is regression-covered without widening the public contract.
- Registered review publication keeps the exact source-tree fast path only for tree-equivalent bases. For a diverged remote default it performs an explicit-base three-way `merge-tree`, publishes the reconciled tree on the exact verified remote-default parent, and fails closed on conflict while retaining ancestry, exact remote SHA, review-branch, lease, and post-publish checks.
- DBHub generated TOML writes are idempotent; Serena child streams are UTF-8 safe and persisted empty generated language state is conservatively repaired from bounded inspected source suffixes; DockerHub now uses current FastMCP `Visibility` transforms.

## Validation evidence

- Final focused workflow/provider regression set: `73/73` passed; the publication suite includes both successful divergent-base reconciliation and conflict fail-closed coverage.
- The real 115/116 concurrency case was replayed with `git merge-tree --write-tree --merge-base`: merging the original 116 delta onto GitHub `main` produced tree `082938bfb9f348a10bef0fa39f41333693cb5ecf`, exactly matching the rebased 116 implementation tree and therefore preserving landed 115 content.
- Final local gates pass on the tree-equivalent source branch: Ruff across all 14 changed Python files, `change-workflow validate --claims-only`, `change-workflow check`, and `git diff --check` all exited `0`; the scope check reports only the 19 declared 116 paths.
- Canonical exact-head verification is pending the corrected PR head.

## CI finding and correction

- The first PR #158 exact-head run (`31733803565`) failed at canonical repository verification because landed change 114 still appeared as an active exclusive claim in that published tree.
- More importantly, that run exposed a concurrency hazard in the first reconciliation design: flattening an older exact source tree onto a newer remote-default parent could overwrite unrelated landed work. That design was rejected before merge.
- Current GitHub `main` `4c0e508c70f69ebdebc52500cc078eca063f5ef0` and local `main` `5f9c60c1bdf363207cddd4a5fa24cc4d006b3e6f` have different commit identities but the same tree `48582444880f96e74f01f9838f0aeb61f3d7bf61`; 116 will use that tree-equivalent relationship for final local source and exact remote publication.

## Review

- Automated code-quality review: unavailable; the default call timed out and the fast NVIDIA retry returned `AGENT_BACKEND_FAILED:NvidiaNimError`.
- Automated safety/security review: unavailable; the fast NVIDIA review returned `AGENT_BACKEND_FAILED:NvidiaNimError`.
- Repository fallback review plus exact-head CI identified the unsafe divergent-base flattening behavior; it has been replaced by explicit-base three-way reconciliation with conflict fail-closed tests. A final fallback diff review is required before publication.
- No policy, credential, production-deploy, or permanent-delete behavior changes.

## Ownership / documentation coordination

- Active change 117 exclusively owns `scripts/change-governance.py`; the tree-equivalent local checker topology observed during integration is not folded into 116 by violating exclusive claims.
- Active change 118 owns the capability/workflow catalogue files. The 116 change record states the corrected reconciliation semantics so that owner can reconcile catalogue wording without an overlapping edit.

## Operator hold

- `SPEC-116` / GitHub issue #156 must remain open and not `Done` after implementation landing until the operator explicitly verifies it.
- Host classifier blocks that occur before KIS executes remain an external platform boundary and will not be bypassed.
- GitHub MCP process-lifetime re-authentication and broad public `project`/`path` aliasing remain explicitly out of scope.
