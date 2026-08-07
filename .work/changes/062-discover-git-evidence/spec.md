# Change Specification: Discover Git Evidence Resilience

- **Change ID**: `062-discover-git-evidence`
- **Status**: Approved for implementation by operator directive against the approved Discover product specification
- **Risk Profile**: standard

## Outcome

Restore bounded local Git evidence for ordinary repositories and linked worktrees whose binary Git index exceeds the small text-metadata byte budget, while preserving canonical path, link/reparse, regular-file, configuration, prompt, network, and bounded-command protections.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `docs/DISCOVER-MODULE-PRODUCT-SPEC.md`.
- Operator evidence: live `inspect_project`/`inspect_change` returned `GIT_METADATA_TOO_LARGE`; current `.git/index` is 109,520 bytes while `git_metadata_max_bytes` is 4,096.
- Owned paths: `src/kis_mcp/discover/git_metadata.py`, `tests/discover/test_git_reader.py`, this change record.
- Shared paths: none.
- Excluded paths: policy, capability composition, scanner relevance, impact engine.
- Dependencies: none.
- Integration owner: none.
- Worktree exception: created manually at the canonical governed path from `origin/main` because local `main` was clean but genuinely divergent; primary checkout was not modified. The claim is registered before implementation edits and must pass governance validation immediately.

## Requirements

- **REQ-001**: A normal Git repository with an index larger than `git_metadata_max_bytes` MUST remain inspectable.
- **REQ-002**: A linked worktree backed by the same large index MUST remain inspectable.
- **REQ-003**: The small byte budget MUST continue to apply to Git text/control metadata that Discover actually reads.
- **REQ-004**: The index path MUST still be canonicalized, remain inside the configured boundary, reject links/reparse points, and be a regular file when present.
- **REQ-005**: No Git command template, environment isolation, network posture, Work policy rule, or public schema may change in this slice.

## Acceptance

1. **Given** a repository whose `.git/index` exceeds 4 KiB, **When** `GitReader.inspect` runs, **Then** repository, branch, head, status, and tracked-file evidence remain available.
2. **Given** a linked worktree over that repository, **When** `GitReader.inspect` runs, **Then** linked-worktree evidence remains available.
3. **Given** oversized `.git` indirection text, **When** metadata validation runs, **Then** `GIT_METADATA_TOO_LARGE` is still returned.
4. Existing unsafe/out-of-boundary/malformed metadata tests remain green.
5. Focused Discover Git tests and repository verification pass on the exact final head.

## Risks and recovery

- Risk: weakening metadata preflight could allow unsafe Git metadata shapes.
- Control: do not remove path-chain or file-type validation; distinguish content-read budgets from presence/type validation for the opaque binary index only.
- Recovery: revert this bounded commit; no migration or generated state is introduced.

## Out of scope

- Raising global Discover output limits.
- Capability search/description/workflow changes.
- Scanner priority or output compaction.
- Change-impact precision.
- `.work` governance evidence policy.
