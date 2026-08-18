# Change Specification: Public Repo Pre Actions Recovery

- **Change ID**: `185-public-repo-pre-actions-recovery`
- **Status**: Approved programme
- **Complexity**: `large`
- **Risk triggers**: `destructive`, `external_action`, `public_contract`, `secrets`, `security`
- **Work Management umbrella**: GitHub issue `#348`

## Outcome

Safely make `kis-mcp` public, restore the exact evidence-backed repository state immediately before GitHub Actions availability was lost while preserving later history, and inventory without implementing valuable post-boundary work for later selective reintroduction.

## Authority and scope

- Repository workflow authority: `AGENTS.md`.
- Local change authority: `scope.json` and this approved change record.
- Work Management umbrella: `#348`.
- Owned repository path: `.work/changes/185-public-repo-pre-actions-recovery/**`.
- Later implementation paths MUST be added to `scope.json` by the specific slice before modification.

## Child issues

- `#349` — public exposure safety audit.
- `#350` — configure and make repository public; depends on `#349` GO.
- `#351` — identify exact pre-Actions recovery boundary.
- `#352` — restore exact pre-Actions baseline; depends on `#351`.
- `#353` — inventory valuable post-boundary work; depends on `#351`; inventory only.

## Requirements

- **REQ-001**: Public visibility MUST NOT change until `#349` records an explicit GO.
- **REQ-002**: The recovery boundary MUST be one evidence-backed immutable commit SHA and tree SHA, not an approximate date or reconstruction.
- **REQ-003**: Restoration MUST preserve later history and stopped work recoverably.
- **REQ-004**: The restored repository tree MUST exactly match the selected pre-Actions baseline.
- **REQ-005**: Post-boundary work under `#353` is identification and classification only; no selective implementation is permitted under Change 185.
- **REQ-006**: Each child issue MUST remain independently reviewable and closable.

## Acceptance

1. `#349` proves publication safety and `#350` verifies the repository is intentionally public with the approved minimum-exposure configuration.
2. `#351` identifies the exact recovery commit/tree from evidence and `#352` verifies the restored `main` tree against it.
3. All later history and paused work remain recoverable.
4. `#353` produces an evidence-linked value inventory and recommended later reimplementation order without implementing any candidate.
5. The umbrella `#348` and Project board reflect all child issue outcomes.

## Risks and recovery

- Public exposure risk is controlled by the mandatory history-aware audit and GO gate.
- Recovery mistakes are controlled by immutable boundary evidence and exact tree verification.
- Stopped post-boundary work is preserved rather than deleted; paused change 184 is currently recoverable from its preserved branch plus stash evidence.

## Out of scope

- Reimplementing any post-boundary feature.
- Resuming the stopped MCP authority implementation.
- Using GitHub Actions as a required landing gate for this programme.
