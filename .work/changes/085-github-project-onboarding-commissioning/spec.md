# Change Specification: GitHub Project Write Commissioning

- **Change ID**: `085-github-project-onboarding-commissioning`
- **Status**: Approved for implementation
- **Development level**: Complex
- **Reason**: live provider mutation and persistent remote Project state require supervised commissioning, rollback, and fresh evidence.

## Outcome

Complete official GitHub Projects write commissioning for `kis-mcp` against the already registered `NielPieterse0` user Project `#1` (`KIS Work Management`). Use change 085's own pull request as the first tracked Project item, then enable supervised reconciliation while leaving every automation mode disabled.

## Authority and isolation

- Authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`.
- Existing central registry, P0-P5 Work Management, GitHub Project adapter, and Project #1 binding remain unchanged architecture.
- Change 084 owns broad Work Management tests and operations documentation; 085 must not edit those paths.
- No second GitHub Project is created.

## Requirements

- **R1**: Preserve `kis-mcp` binding to `NielPieterse0`, owner type `user`, Project `#1`, stable Work Management binding `github-default`.
- **R2**: Prove live inventory reports Project title `KIS Work Management`, open state, complete pagination, and `Status` options `Todo`, `In Progress`, `Done`.
- **R3**: Use 085's pull request as the first tracked item and use the existing bounded Project/Work Management path for commissioning mutations.
- **R4**: Prove add/update behavior, no duplicate source item on replay, and stale-revision conflict protection without overwrite.
- **R5**: After write commissioning evidence, change only `features.reconciliation` from `read_only` to `enabled`.
- **R6**: Keep `intake` and `review_import` read-only, `programme_status` enabled, and every automation flag `false`.
- **R7**: Add focused regression coverage and commissioning evidence without changing provider auth, GraphQL exposure, deletion behavior, or unrelated Work Management architecture.

## Acceptance

1. Checked-in settings and registry still resolve `kis-mcp` to user Project #1 and stable backend binding `github-default`.
2. Fresh live inventory confirms Project #1 identity and the exact required `Status` options with no truncation.
3. Before promotion, a focused regression test fails because reconciliation is still `read_only`.
4. 085's PR is added exactly once, then set to `In Progress`; replay does not create a duplicate.
5. A stale-revision update returns conflict and does not overwrite newer Project state.
6. After commissioning, focused tests prove reconciliation is `enabled` and all six automation flags remain `false`.
7. Scope check, code review, and canonical repository verification are run on the final branch state; any unrelated baseline failure is recorded rather than edited around.
8. After landing, the tracked PR item is set to `Done` and final inventory confirms exactly one matching item.

## Risks and recovery

- Remote commissioning changes one Project item only. Recovery is a bounded Status update through the same Project path; deletion is neither needed nor authorized.
- Enabling reconciliation exposes supervised apply capability, but apply still requires `apply=true` and a non-empty idempotency key; automation remains off.
- GitHub OAuth is runtime-scoped. If the provider requests authentication, the operator completes the normal supervised browser flow and keeps that runtime alive.
- Windows Application Control blocks the `pytest.exe` shim on this machine; focused tests use the locked interpreter with `python.exe -m pytest`.

## Out of scope

- New Project creation, `college`, `gpt-os`, views, native GitHub automation, issue types, unrestricted GraphQL, delete/archive, provider/auth changes, Discover/memory/startup work, or general Work Management redesign.
