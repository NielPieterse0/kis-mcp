# Change Specification: Instance Startup Lifecycle Hardening

- **Change ID**: `059-instance-startup-lifecycle-hardening`
- **Status**: Approved
- **Development level**: Medium

## Outcome

Make ChatGPT runtime startup deterministic and self-healing for the selected instance only, while preserving the independently running peer instance.

## Requirements

- Starting `operation` may inspect, reclaim, and clean only `operation` runtime/process state and port 8010.
- Starting `development` may inspect, reclaim, and clean only `development` runtime/process state and port 8011.
- Never terminate or mutate the peer instance as part of selected-instance startup.
- Reclaim a selected port only when its listener is positively identified as the selected KIS instance; unrelated listeners must fail with diagnostics.
- Detect and terminate orphaned selected-instance KIS server and tunnel process trees before starting replacements.
- Record one authoritative per-instance `current.json` ownership record with run, process, executable, endpoint, and lifecycle state.
- Prove after startup that the newly created selected-instance process tree owns the configured port before declaring readiness.
- Enforce the canonical external Python environment and recoverably quarantine repository-local stale `.venv` and `.pytest_cache` artifacts.
- Retain historical startup/log evidence; do not infer current ownership from newest timestamped files.
- Keep HR-001 through HR-003 unchanged and perform no permanent deletion.

## Acceptance

1. A-running/start-B leaves A alive and B starts on B's configured port.
2. B-running/start-A leaves B alive and A starts on A's configured port.
3. stale-A/start-A reclaims only stale A processes and starts a fresh A runtime.
4. stale-B/start-B reclaims only stale B processes and starts a fresh B runtime.
5. an unrelated listener on the selected port is never killed and startup fails with PID/process diagnostics.
6. `current.json` identifies the selected runtime that actually owns the endpoint and is marked stopped during owned shutdown.
7. repository-local stale runtime/cache artifacts are moved recoverably, not permanently deleted.

These are implementation acceptance criteria. Live `kis-dev` startup from merged `main` remains a separate operator-supervised commissioning check because vault unlock and tunnel credentials are not available to unattended verification.

## Out of scope

- Work-management commissioning in change 058.
- Changes to the three-rule policy.
- Automatic cleanup of the peer instance.
- Permanent disposal of historical logs or quarantine content.

Change 058 released its unused exclusive claim on `docs/OPERATIONS.md`; this slice owns and reconciles the startup-lifecycle documentation.