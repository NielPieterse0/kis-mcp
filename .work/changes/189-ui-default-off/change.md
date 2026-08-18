# Change: UI Default Off

- **Change ID**: `189-ui-default-off`
- **Risk Profile**: lean
- **Parent**: Change 186 / issue #356
- **Work item**: issue #359

## Outcome

Restore Control Center UI as explicit opt-in by keeping the gateway provider disabled by default while preserving standalone/operator enablement.

## Scope and acceptance

- Only declared runtime settings, focused provider tests, current `SPEC.md`, and this change record are modified.
- `control-center` remains registered at namespace `controlcenter` but checked-in `enabled=false`.
- All other configured gateway providers remain enabled.
- Standalone Control Center remains available.

## Implementation and verification

- Implementation notes: historical Change 171 behavior was reimplemented semantically on reconstructed `main`; no stale historical file version was copied wholesale.
- Focused checks: 21 provider-runtime tests passed; Ruff passed; scope check passed.
- Review findings: exact frozen-head specialist review runs in parallel with GitHub Actions.
- Residual risk: none beyond explicit operator enablement behavior already supported by runtime settings.
- Closeout state: ready for frozen-head PR gate.