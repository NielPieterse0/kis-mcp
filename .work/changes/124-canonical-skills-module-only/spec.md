# Change Specification: Canonical Skills Module Only

- **Change ID**: `124-canonical-skills-module-only`
- **Status**: Approved for implementation by operator instruction
- **Complexity**: `medium`
- **Risk triggers**: `public_contract`

## Outcome

Remove repository-local skills and require all reusable skill discovery, loading, and reference-file access to flow through the KIS Skills module backed by the canonical shared catalogue.

## Authority and scope

- `AGENTS.md` remains repository workflow authority.
- Runtime Skills implementation remains owned by `SPEC.md` and `docs/SKILLS-MODULE-PRODUCT-SPEC.md`.
- Historical `.work/changes/**` records remain historical evidence and are not rewritten solely to erase former paths.
- Change 120 is already merged through PR #172; only its stale `scope.json` status may be reconciled to release obsolete path ownership needed by this change.

## Requirements

- **REQ-001**: No tracked file may remain beneath repository `.agents/skills/**`.
- **REQ-002**: Current repository authority/guidance MUST instruct agents to use Skills-module operations (`search_skills`, `load_skill`, `read_skill_file`) rather than direct filesystem skill loading.
- **REQ-003**: The shared `C:\Projects\.agents\skills` location remains an implementation detail of the Skills module, not an agent-facing bypass path.
- **REQ-004**: CI and canonical verification MUST NOT seed the shared catalogue by copying repository-local skills.
- **REQ-005**: Verification/tests MUST fail when tracked repository-local skills or current operational guidance to load them is reintroduced.
- **REQ-006**: Existing runtime behavior and HR-001/HR-002/HR-003 semantics remain unchanged.

## Acceptance

1. The repository tracks no reusable skill package beneath its local agent metadata tree.
2. Current authority instructs agents to use `search_skills`, `load_skill`, `search_skill_files`, and `read_skill_file` rather than direct filesystem skill loading.
3. CI passes without copying skill content from the repository checkout into the shared catalogue.
4. Focused verification rejects reintroduction of a repository-local skill catalogue.
5. `scripts/change-workflow.ps1 check` and affected tests pass for the final exact change.

## Risks and recovery

- Risk: hidden CI or fixture coupling to the removed checked-in copies.
- Mitigation: focused tests plus canonical verification guard before publication.
- Recovery: the removed worktree content is retained intact in quarantine and remains recoverable from Git history.

## Out of scope

- Changing canonical shared skill contents.
- Rewriting historical change evidence solely to remove old path mentions.
- Changing Skills service behavior or any Work hard rule.
