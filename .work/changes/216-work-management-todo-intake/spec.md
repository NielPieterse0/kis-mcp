# Change Specification: Work Management Todo Intake

- **Change ID**: `216-work-management-todo-intake`
- **Status**: Active

## Outcome

Make provider-default GitHub Project `Todo` intake enter the declared Work Management command plane without bypassing Work Management authority.

## Authority and scope

- `AGENTS.md` remains repository workflow authority.
- `SPEC.md` owns current implemented Work Management behavior.
- `settings/work-management/command-plane.settings.json` owns command-plane states and intake aliases.
- `contracts/work-management/command-plane.settings.schema.json` owns the settings contract.
- Implementation is bounded to command settings, transition-state resolution, tests, and the current product specification.

## Requirements

- **REQ-001**: A configured provider-default intake alias maps an undeclared provider state to one declared command-plane state.
- **REQ-002**: GitHub Project `Todo` maps to command-plane `inbox`.
- **REQ-003**: Legitimate declared lifecycle states are not rewritten or aliased.
- **REQ-004**: Existing `Todo` items can progress through declared transitions to `Ready` while preserving Ready metadata gates.
- **REQ-005**: Unknown undeclared states remain fail-closed.
