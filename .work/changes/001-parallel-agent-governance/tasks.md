# Tasks: Parallel Agent Governance

- [x] Review `GPT-OS`, `doc-solution`, and Superpowers workflow guidance.
- [x] Remove abandoned contract worktrees and safely deletable duplicate branches.
- [x] Create `change/001-parallel-agent-governance` at `.work/worktrees/001-parallel-agent-governance`.
- [x] Implement and test claim validation.
- [x] Implement and test worktree lifecycle commands.
- [x] Add templates and repository authority updates.
- [x] Integrate governance validation into repository verification.
- [x] Run scope check, diff review, and full verification.
- [x] Commit, merge, and clean the worktree.

## Deferred and external state

- Force deletion of the unmerged `feat/lean-contract-baseline` local branch is prohibited by the available immutable Git rule. It remains only as a recovery reference with no active worktree.
- The separately owned `change/002-modularity-contracts` and `change/003-quarantine-integrity` worktrees are active but have no registered change claims. The validator reports the first missing claim and both missing `scope.json` files were confirmed without modifying either worktree.
