# Change Specification: Control Center UI Default-Off

- **Change ID**: `189-ui-default-off`
- **Status**: Active
- **Parent**: Change 186 / issue #356
- **Work item**: issue #359
- **Historical source**: Change 171 implementation `553a23c`

## Outcome

Keep the Control Center provider available but disabled in the checked-in gateway composition by default, preserving explicit operator enablement and standalone launch.

## Requirements

- `control-center` remains a registered provider record with namespace `controlcenter`.
- Its checked-in runtime `enabled` value is `false`.
- All other configured runtime providers remain enabled.
- Standalone Control Center behavior remains available and unchanged.
- Documentation describes default-off/explicit-enable behavior without changing Work policy authority.

## Acceptance

Focused provider-runtime tests and Ruff pass; scope check passes; specialist review and GitHub Actions pass on the frozen exact head.