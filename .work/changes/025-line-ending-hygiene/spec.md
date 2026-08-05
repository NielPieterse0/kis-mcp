# Change Specification: Line Ending Hygiene

- **Change ID**: `025-line-ending-hygiene`
- **Status**: Approved
- **Risk Profile**: standard

## Outcome

Make LF the canonical repository text format across Windows worktrees and prevent rebases, whitespace checks, editors, or Git configuration from repeatedly creating false CRLF-only modifications.

## Authority and scope

- Authorities: `AGENTS.md`, repository verification rules, and the operator-approved recommendation.
- Owned paths are recorded in `scope.json`.
- No product behavior, policy rule, provider behavior, or active feature slice is changed.

## Requirements

- **REQ-001**: Commit `.gitattributes` with LF for repository text and explicit binary handling.
- **REQ-002**: Commit `.editorconfig` with UTF-8, LF, final newline, and trailing-whitespace cleanup.
- **REQ-003**: Configure repository-local Git with `core.autocrlf=false`, `core.eol=lf`, and `core.safecrlf=true` through normal workflow and verification entry points.
- **REQ-004**: Renormalize tracked text once without semantic content changes.
- **REQ-005**: Verification must reject CRLF or mixed index/worktree text governed by LF attributes.

## Acceptance

1. Focused regression tests fail before implementation and pass afterward.
2. `git ls-files --eol` reports LF for every tracked file governed by `eol=lf`.
3. `git diff --check` passes after renormalization.
4. Change-scope and full repository verification pass on the final branch.

## Risks and recovery

- Risk: one large mechanical diff can hide semantic changes.
- Control: review with `--ignore-space-at-eol`, explicit file lists, and current tests.
- Recovery: revert the hygiene commit; the operator settings change remains outside this branch.

## Out of scope

- Feature implementation, provider commissioning, policy changes, and permanent changes to system-wide Git configuration.
