# Change: Work Management Project Onboarding

- **Change ID**: `115-work-management-project-onboarding`
- **Risk Profile**: lean
- **Development level**: Small — bounded configuration/test/documentation expansion; no new provider, policy, backend, or runtime interface.

## Outcome

Onboard `chatgpt-skill`, `commodity`, and `college` into the existing shared Work Management portfolio while retaining `kis-mcp`, and list this slice as `SPEC-115`.

## Scope and acceptance

- Reuse user Project #1 and stable backend binding `github-default`.
- Keep the Project coordinate registered once under `kis-mcp`; do not duplicate one GitHub Project coordinate across registry entries.
- Add all four repositories to `managed_projects` with their existing central-registry repository identities.
- Preserve disabled automation, the existing 18-field/12-view target, and Work Management's projection-only authority.
- Track GitHub issue #154 as the `SPEC-115` source record in Project #1.

## Implementation and verification

- TDD red: onboarding test failed because `chatgpt-skill` was not yet managed; an attempted duplicated Project coordinate then correctly failed the registry uniqueness invariant.
- Implementation: expanded only `managed_projects`; no project-registry code or policy behavior changed.
- Focused checks: 21 onboarding, Work Management settings/registry-binding, and project-registry tests pass.
- Scope/diff checks: `change-workflow.ps1 check` and `git diff --check` pass on the implementation tree.
- First exact-head CI run stopped at governance because already-merged change 114 still had stale `status=ready` claims over `SPEC.md` and `docs/OPERATIONS.md`; configuration, dependencies, and Python syntax had already passed.
- Landing-blocker correction: change 114 is now `closed` with `post_merge_complete`, and this exact lifecycle artifact is explicitly owned by change 115.
- Review finding resolved: shared Project identity must be registered once rather than copied into every repository entry.
- Residual risk: rich Project fields/views remain the existing separate commissioning gap; this slice does not alter it.
- Closeout state: implementation and focused local verification complete; corrected exact-head PR verification remains the landing gate.
