# Change Specification: Env Expanded Shell Mutations

- **Change ID**: `164-env-expanded-shell-mutations`
- **Status**: Active
- **Develop-code level**: Complex — security/trust-boundary behavior
- **Repository governance complexity**: Medium
- **Risk profile**: Rigorous

## Outcome

Fail closed before forwarding when a syntactically definite shell mutation target cannot be resolved safely, including environment-variable and PowerShell subexpression syntax, without treating uncertainty itself as HR-001 or HR-003 evidence.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `policy/kis-mcp.policy.json`, GitHub issue #288.
- Owned paths: `src/kis_mcp/models.py`, `src/kis_mcp/command_intent.py`, `src/kis_mcp/policy.py`, `src/kis_mcp/shell_parser.py`, focused parser/policy/middleware/process-state tests, and this change directory.
- Excluded: #270, #278, #241, #258, #289 and unrelated cleanup/reconciliation work.
- Dependencies: none.
- Integration owner: this isolated change only.

## Requirements

- **REQ-001**: Preserve syntactically definite write, entry, and delete targets when static path resolution fails instead of dropping them from `InvocationEffects`.
- **REQ-002**: Represent unresolved target-bearing mutations separately from targetless destructive intent such as `git clean`.
- **REQ-003**: Reject unresolved definite mutation targets structurally with `INVALID_INVOCATION_PATH` and no HR rule attribution.
- **REQ-004**: Cover cmd `%VAR%` and modifier forms, cmd `!VAR!` only when delayed expansion is enabled, PowerShell `$env:VAR`, ordinary/scoped variables, `${...}`, `$()`, and wrapped/nested shell forms for redirection, write, delete, move, and create paths.
- **REQ-005**: Track cmd delayed-expansion state across one-shot and persistent shells, honor the last `/V:ON` or `/V:OFF` wrapper switch before `/c` or `/k`, and ignore `/V:` text inside the payload.
- **REQ-006**: Preserve normal literal in-boundary allow/quarantine behavior, including literal `%`, disabled `!name!`, and single-quoted PowerShell markers, plus the trust-model rule that unknown commands or generic uncertainty alone are not blockable.
- **REQ-007**: Preserve the existing positional constructor meaning of the original `InvocationEffects` and `ShellState` fields.
- **REQ-008**: Structural invalid-invocation evidence takes precedence over HR attribution when a definite unresolved mutation target is present alongside otherwise classifiable effects.

## Acceptance

1. **Given** a wrapped shell command with an environment-expanded or subexpression mutation target, **when** effects are resolved, **then** unresolved mutation evidence is retained.
2. **Given** unresolved definite mutation evidence, **when** policy is evaluated, **then** the decision is `BLOCK` / `INVALID_INVOCATION_PATH` with `rule_id=None`.
3. **Given** such a command reaches middleware, **when** policy runs, **then** the provider command is not forwarded.
4. **Given** literal in-boundary mutations, **when** evaluated, **then** existing allow/quarantine behavior remains unchanged.
5. **Given** an unknown command containing environment syntax but no syntactically identified mutation, **when** effects are resolved, **then** no unresolved mutation evidence is created.
6. Focused parser/policy/middleware tests, repository scope check, required specialist reviews, and exact-head Canonical Verification pass.

## Risks and recovery

- Risk: over-classifying ordinary shell syntax as a mutation target. Mitigation: unresolved evidence is emitted only from existing syntactically identified mutation-target extractors.
- Risk: changing `InvocationEffects` compatibility. Mitigation: append new fields after the original positional fields and retain `unresolved_delete` semantics.
- Recovery: revert the isolated merge; no persistent data, migration, external state schema, or destructive operation is introduced.

## Out of scope

- Evaluating or expanding shell environment variables/subexpressions inside KIS.
- Blocking unknown commands merely because their effects are uncertain.
- Changing HR-001, HR-002, or HR-003 definitions.
- Broader command-language redesign outside definite mutation-target preservation.
