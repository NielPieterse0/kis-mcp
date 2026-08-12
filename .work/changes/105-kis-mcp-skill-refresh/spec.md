# Change Specification: kis-mcp Skill Refresh

- **Change ID**: `105-kis-mcp-skill-refresh`
- **Status**: Approved by operator request
- **Documentation level**: Medium — multi-file procedural skill refresh
- **Risk Profile**: standard

## Outcome

Refresh the repository-local `kis-mcp` operating skill so users can reach the latest implemented KIS workflows quickly, understand which layer to use, and avoid manually recreating orchestration that the platform already provides. Keep Slice 7 top-level delivery coordination explicitly in-progress rather than presenting it as deployed.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, and `docs/OPERATIONS.md`.
- Implementation evidence: closed changes 093, 096, 097, 098, 099, 100, 101, and 103; locally merged Slice 6 change 104; and the declared active Slice 7 contract in change 106.
- Guidance sources: repository-local `mcp-development` plus shared `create-skill` and `improve-skill` material, subordinate to repository authority.
- Owned paths: `.agents/skills/kis-mcp/**` and this change record.
- Excluded: runtime code, settings, policy, external credentials, provider installation, and unrelated documentation.

## Requirements

- **REQ-001**: Put common user intents first and route each to the smallest direct tool or workflow.
- **REQ-002**: Cover change intelligence, Python quality evidence, agnix validation, specialist reviews, verification selection/execution, workflow recommendation, and safe closeout behavior.
- **REQ-003**: Distinguish implemented behavior, live-runtime availability, Slice 6 delivery state, and Slice 7 in-progress coordination.
- **REQ-004**: Preserve project-neutral routing and exactly HR-001/HR-002/HR-003; skill prose must not create authority.
- **REQ-005**: Keep `SKILL.md` compact and move detailed schemas/operator procedures to focused references.

## Acceptance

1. A user can map status, project inspection, change analysis, planning, verification, review, agent-config validation, and PR closeout requests to the correct KIS surface without memorizing the catalogue.
2. `select_change_verification` is described as read-only selection; `execute_change_workflow` as bounded execution/aggregation; quality tooling evidence is not misrepresented as automatic installation or execution.
3. All seven supported review purposes are discoverable from the skill without broadening reviewer authority.
4. Slice 7 is described as remaining top-level delivery coordination, with explicit live-capability checks before use.
5. Frontmatter, relative references, line endings, scope checks, and canonical repository verification pass on the final state.

## Risks and recovery

- Risk: procedural prose may outrun the running instance. Mitigation: live schemas/capability evidence remain authoritative and in-progress features are clearly labeled.
- Risk: duplicated implementation status can become stale. Mitigation: keep detailed current truth in canonical owners and use this skill for task routing and status boundaries only.
- Recovery: revert the skill-only change; no runtime state or policy migration is involved.

## Out of scope

- Implementing Slice 7 or changing Slice 6 runtime code/delivery.
- Changing provider schemas, direct-profile membership, Work policy, credentials, or project bindings.
- Turning advisory Govern/review/selection metadata into a blocking permission system.
