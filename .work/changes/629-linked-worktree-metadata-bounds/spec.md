# Change Specification: Linked Worktree Metadata Bounds

- **Change ID**: `629-linked-worktree-metadata-bounds`
- **Status**: Implemented; pending publication and merge
- **Complexity**: `medium`
- **Risk triggers**: `security`

## Outcome

Make bounded Git evidence inspection accept legitimate repository-scale active config and packed-refs metadata in linked worktrees without weakening pointer/path/link safety, with regression coverage and live commodity verification.

## Authority and scope

- Authority: `AGENTS.md`, current Discover implementation/settings, and `scope.json`.
- Owned implementation: `src/kis_mcp/discover/git_metadata.py`, `src/kis_mcp/discover/git_reader.py`.
- Owned tests: `tests/discover/test_git_reader.py`.
- No shared paths or dependencies.

## Requirements

- **REQ-001**: Keep the configured 4 KiB control-metadata bound for `.git` pointers, `commondir`, `HEAD`, loose refs, and alternates.
- **REQ-002**: Read active Git config files and `packed-refs` using the existing bounded Git-output byte budget rather than the control-pointer limit.
- **REQ-003**: Preserve boundary, canonical-path, regular-file identity, symlink/reparse, include-depth, and bounded-read protections.
- **REQ-004**: Regress legitimate linked worktrees whose active config or packed refs exceed 4 KiB.

## Acceptance

1. Linked worktree inspection succeeds with active config larger than `git_metadata_max_bytes` but below `git_max_output_bytes`.
2. Linked worktree inspection succeeds with `packed-refs` larger than `git_metadata_max_bytes` but below `git_max_output_bytes`.
3. Existing unsafe, outside-boundary, malformed, non-directory, and oversized control-pointer cases continue to fail closed.
4. Scope check, focused tests, required code-quality review, and required safety-security review pass.
