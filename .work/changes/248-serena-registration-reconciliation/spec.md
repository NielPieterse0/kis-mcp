# Change Specification: Serena Registration Reconciliation

- **Change ID**: `248-serena-registration-reconciliation`
- **Status**: Approved
- **Development level**: Medium
- **Risk trigger**: `persistent_state`

## Outcome

Reconcile Serena generated project registrations against current project/worktree truth before provider startup so removed governed worktrees do not remain registered.

## Authority and scope

- `AGENTS.md` governs repository workflow and generated-state boundaries.
- `SPEC.md` defines Serena as optional read-only semantic enrichment; repository/Git/document evidence remains authoritative.
- Work #527 defines the stale-registration lifecycle requirement.
- Owned implementation: `src/kis_mcp/providers/serena/adapter.py`.
- Owned regression coverage: `tests/providers/test_serena_registration_reconciliation.py`.

## Requirements

- **REQ-001**: Before Serena starts, reconcile the generated `projects:` list in `serena_config.yml` against filesystem truth.
- **REQ-002**: Remove only registrations whose resolved project paths no longer exist; preserve active registrations unchanged and in stable order.
- **REQ-003**: Treat Serena registration state as generated provider state only; it must not create repository authority.
- **REQ-004**: Reconciliation must be deterministic, bounded to Serena generated state under `C:\Projects\.kis-mcp`, and safe across restart.
- **REQ-005**: Do not delete repository or governed change evidence; HR-003 remains unchanged.

## Acceptance

1. Given a Serena config containing an existing project and a removed worktree, reconciliation removes only the missing path.
2. Given only active project registrations, reconciliation is idempotent and preserves the config.
3. Provider startup runs reconciliation before constructing the Serena transport.
4. Focused regression tests and change-governance checks pass.

## Risks and recovery

- Risk: malformed or unexpected Serena YAML could be rewritten incorrectly.
- Mitigation: only rewrite a uniquely identified top-level `projects:` block; otherwise fail without mutation.
- Recovery: generated Serena config can be recreated by the pinned provider bootstrap; repository evidence is untouched.

## Out of scope

- Changing Serena package/version or its public tool surface.
- Changing governed worktree cleanup semantics.
- Treating Serena registrations as authoritative project inventory.
