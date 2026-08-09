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
- **R3**: Use GitHub issue #102 for change 085 as the first tracked Project item and use the existing bounded GitHub Project/Work Management path for commissioning mutations.
- **R4**: Normalize the official provider's live REST Project item shape: integer `id`, `content_type`, `fields`, `html_url`, and write responses containing numeric `item_id` plus node `id`.
- **R5**: Preserve provider-neutral string IDs by converting positive numeric Project item IDs to digit text and prefer `item_id` over node `id` for write follow-up calls.
- **R6**: Prove add/update behavior, no duplicate source item on replay, and stale-revision conflict protection without overwrite.
- **R7**: After write commissioning evidence, change only `features.reconciliation` from `read_only` to `enabled`.
- **R8**: Keep `intake` and `review_import` read-only, `programme_status` enabled, and every automation flag `false`.
- **R9**: Add focused regression coverage and commissioning evidence without changing provider auth, GraphQL exposure, deletion behavior, or unrelated Work Management architecture.

## Acceptance

1. Checked-in settings and registry still resolve `kis-mcp` to user Project #1 and stable backend binding `github-default`.
2. Fresh live inventory confirms Project #1 identity and the exact required `Status` options with no truncation.
3. Before promotion, a focused regression test fails because reconciliation is still `read_only`.
4. Live REST-shaped item evidence normalizes successfully and follow-up writes use the numeric Project item ID as digit text rather than the GraphQL node ID.
5. Issue #102 is present exactly once and has `Status=In Progress`; replay does not create a duplicate.
6. A stale-revision update returns conflict and does not overwrite newer Project state.
7. After commissioning, focused tests prove reconciliation is `enabled` and all six automation flags remain `false`.
8. Scope check, code review, and canonical repository verification are run on the final branch state; any unrelated baseline failure is recorded rather than edited around.
9. After landing, issue #102 is set to `Done` and final inventory confirms exactly one matching item.

## Risks and recovery

- Remote commissioning changes one Project item only. Recovery is a bounded Status update through the same Project path; deletion is neither needed nor authorized.
- Enabling reconciliation exposes supervised apply capability, but apply still requires `apply=true` and a non-empty idempotency key; automation remains off.
- GitHub OAuth is runtime-scoped. If the provider requests authentication, the operator completes the normal supervised browser flow and keeps that runtime alive.
- Windows Application Control blocks the `pytest.exe` shim on this machine; focused tests use the locked interpreter with `python.exe -m pytest`.

## Out of scope

- New Project creation, `college`, `gpt-os`, views, native GitHub automation, issue types, unrestricted GraphQL, delete/archive, provider/auth changes, Discover/memory/startup work, or general Work Management redesign.
