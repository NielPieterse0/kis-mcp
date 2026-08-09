# Change Specification: Restart Finalizer Hardening

- **Change ID**: `083-restart-finalizer-hardening`
- **Status**: Active
- **Risk Profile**: standard
- **Development Level**: Medium

## Outcome

A displaced selected-instance launcher must exit without a StrictMode error when a replacement startup has already rewritten `current.json` to a restart handoff state that intentionally has no `run_id`.

## Requirements

- **REQ-001**: `Set-KisMcpCurrentInstanceStopped` must tolerate a valid state document without `run_id` and leave that newer state unchanged.
- **REQ-002**: A matching `run_id` must still transition only that launcher-owned state to `stopped`.
- **REQ-003**: A different `run_id` must remain untouched.
- **REQ-004**: No process ownership, port reclaim, peer-instance, or hard-rule behavior may change.

## Acceptance

1. Given `current.json` with `lifecycle=restarting` and no `run_id`, calling the old launcher's stopped-state finalizer returns successfully and preserves `restarting`.
2. Existing matching-run and mismatched-run semantics remain covered.
3. Focused startup tests and canonical repository verification pass.

## Risks and recovery

- Risk: a finalizer could overwrite state owned by the replacement launcher. Mitigation: absence or mismatch of `run_id` returns without mutation.
- Recovery: revert this small state-guard change; replacement startup itself remains functional but the displaced launcher may emit the observed StrictMode error.

## Out of scope

- Changing restart/reclaim matching logic implemented by change 082.
- Supabase shared-runtime smoke repair.
- Provider authentication or tunnel behavior.
