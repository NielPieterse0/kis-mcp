# Change Specification: Parallel Agent Governance

- **Change ID**: `001-parallel-agent-governance`
- **Status**: Approved
- **Risk Profile**: standard

## Outcome

Allow any practical number of parallel agents while preventing duplicate or unclaimed scope. Every implementation change receives one stable change ID, one declared outcome, explicit path claims, and a standardized worktree under `.work/worktrees/<change-id>`.

## Requirements

- **REQ-001**: Provide a repository command that creates a change branch and worktree only after validating the proposed claim against active worktrees.
- **REQ-002**: Reject duplicate change IDs, branches, worktree paths, normalized outcomes, and overlapping exclusive path claims.
- **REQ-003**: Permit intentional shared-path overlap only when both claims declare the path as shared and coordination is explicit through a dependency or integration owner.
- **REQ-004**: Provide a current-change check that compares the actual base-to-head and working-tree diff with declared owned, shared, and excluded paths.
- **REQ-005**: Provide safe cleanup for clean worktrees whose branches are already merged into their declared base; never force-remove a dirty or unmerged branch.
- **REQ-006**: Store scope, specification, plan, tasks, and closeout artifacts under `.work/changes/<change-id>/` and provide tracked templates.
- **REQ-007**: Integrate repository-layout validation into `scripts/verify.py` and document the workflow in `AGENTS.md` and `docs/OPERATIONS.md`.

## Constraints

- Do not limit the number of active agents or worktrees.
- Do not add a runtime policy rule or modify HR-001 through HR-003.
- Do not add dependencies, services, databases, locks, leases, or agent heartbeats.
- Use exact paths or recursive `/**` claims; reject ambiguous glob syntax.
- Keep all Git cleanup non-force and recoverable through retained commit IDs and Git reflogs.

## Acceptance

- A second active change with the same outcome is rejected.
- Exclusive path overlap is rejected before worktree creation.
- Coordinated shared overlap is accepted.
- An undeclared or excluded changed path fails the current-change check.
- A new change is created at `.work/worktrees/<change-id>` with all required artifacts.
- Cleanup refuses dirty or unmerged worktrees and removes only a clean merged worktree.
- Full repository verification passes.
