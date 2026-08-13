# Change Specification: Skills Catalogue Reconciliation

- **Change ID**: `121-skills-catalogue-reconciliation`
- **Status**: Approved for urgent implementation
- **Complexity**: medium
- **Risk triggers**: `public_contract`

## Outcome

Restore KIS startup while making the shared Skills catalogue safely dynamic: discover only `C:\Projects\.agents\skills`, tolerate valid skills without private KIS capability metadata, require canonical `kis-mcp`, and remove the duplicate repository-local `kis-mcp` package.

## Authority and scope

- Existing repository authority governs implementation; 121 does not rewrite authority claimed by another active change.
- `settings/skills.settings.json` owns canonical Skills root and required runtime skill identity.
- `settings/capabilities.settings.json` remains optional enhancement metadata, not catalogue membership authority.
- Existing `SPEC.md` already states runtime Skills resolve exclusively from `C:\Projects\.agents\skills`.
- `AGENTS.md`, `SPEC.md`, `docs/OPERATIONS.md`, and active change 120's workflow are excluded from 121.
- Manual worktree creation was required because active 120 carries a legacy documentation-impact value rejected by current intake validation.

## Requirements

- **REQ-001**: Startup scans only the canonical shared Skills root on runtime construction.
- **REQ-002**: A valid shared skill without KIS capability metadata remains listable/loadable and cannot fail gateway capability composition.
- **REQ-003**: Only explicitly classified skills contribute enhanced KIS capability records.
- **REQ-004**: `kis-mcp` is a required canonical skill and missing/invalid canonical presence produces a specific Skills configuration failure.
- **REQ-005**: The repository-local `.agents/skills/kis-mcp` duplicate is removed recoverably; the canonical shared copy is untouched.
- **REQ-006**: Canonical Verification provisions mandatory canonical `kis-mcp` test input independently of the deleted repository-local runtime copy; production verification still fails when the real canonical skill is absent.
- **REQ-007**: Post-merge reconciliation records exact merge/commissioning evidence and any authority wording still implying repository-local skill loading.

## Acceptance

1. An unclassified valid Skill contributes no fabricated enhanced capability and does not raise during capability assembly.
2. Missing configured `kis-mcp` fails with `SKILLS_REQUIRED_MISSING`.
3. `kis-mcp` plus arbitrary valid new Skills builds deterministically and remains discoverable.
4. Focused Skills/capability/gateway/repository-scope tests pass from the locked interpreter.
5. The repository-local `kis-mcp` package is absent and the canonical shared copy remains present.
6. PR-context governance and exact-head Canonical Verification pass.
7. `kis-op` startup smoke passes after landing.

## Risks and recovery

- Optional catalogue members must never become fatal merely because private KIS enhancement metadata is absent.
- Mandatory-skill validation is separate from optional enhancement metadata.
- GitHub Actions may synthesize a minimal canonical test fixture only on an ephemeral runner; production must use the operator-managed canonical skill.
- The removed repo-local duplicate has a verified recovery copy at `C:\Projects\.kis-mcp\temp\121-repo-local-kis-mcp-backup`.

## Documentation impact

Pre-merge documentation is complete in this change record and source issue. Post-merge reconciliation remains required for exact landing and commissioning evidence.
