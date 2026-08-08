# Change Specification: Skills Asset Compatibility

- **Change ID**: `081-skills-asset-compatibility`
- **Status**: Active
- **Development level**: Medium — shared Skills configuration/schema plus catalogue and capability integration across multiple files, with bounded reversible behavior.

## Outcome

Restore the Skills catalogue against the operator-approved shared skill root after packaged skills introduced legitimate larger assets, additional text asset suffixes, extensionless `LICENSE` files, and 12 catalogue entries without capability metadata.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`.
- Owned paths: exactly those declared in `scope.json`; no policy files or unrelated runtime modules.
- Base: `main`; branch: `change/081-skills-asset-compatibility`.
- Invariants: exactly HR-001/HR-002/HR-003; shared Skills root remains `C:\Projects\.agents\skills`; unknown extensionless files remain rejected; no inferred/fallback skill capabilities.

## Requirements

- **R1**: Permit the observed safe packaged text asset suffixes `.svg`, `.css`, `.html`, `.js`, and `.ttl` through JSON-governed validation.
- **R2**: Permit only explicitly configured extensionless text filenames, initially exact `LICENSE`, consistently for catalogue reading and replacement validation; continue rejecting other extensionless files.
- **R3**: Raise JSON-governed Skills limits only enough to contain the observed packaged assets: 2,000,000 bytes/file and 3,000,000 bytes/skill.
- **R4**: Add explicit reviewed capability metadata for all 12 newly installed shared Skills so catalogue composition remains complete.
- **R5**: Keep capability-card count assertions derived from settings where the count is a composition contract rather than a fixed product constant.

## Acceptance

1. Current approved shared Skills catalogue loads successfully under the configured limits and validation contract.
2. A skill containing `LICENSE` loads and permits validated text replacement, while an otherwise equivalent skill containing unconfigured extensionless `NOTICE` fails with `SKILLS_SUFFIX_FORBIDDEN`.
3. Skills and capability-focused tests pass, including the Gateway composition cases that reproduced the primary-main failure.
4. `scripts/change-workflow.ps1 check` and `scripts/verify.ps1` pass on the final 081 worktree state.
5. After landing and governed cleanup, canonical verification passes on primary `main`, with only primary `main` plus preserved clean change 040 remaining.

## Risks and recovery

- Larger configured limits increase bounded catalogue read exposure; limits remain below 2 MB/file and 3 MB/skill and are explicit JSON settings.
- New suffixes can contain executable-looking source, but Skills loading remains data/procedure ingestion only and does not execute arbitrary skill assets.
- Exact filename allowance is fail-closed: only configured names are accepted; arbitrary extensionless content remains rejected.
- Recovery is an ordinary revert of the 081 merge if post-merge canonical verification regresses; no data migration or destructive transition is involved.

## Out of scope

- Changing the shared skill root, three-rule policy, provider authentication, project registry, or runtime execution model.
- Adding inferred/default capability metadata for unknown Skills.
- Broad extensionless-file support or unbounded asset limits.
