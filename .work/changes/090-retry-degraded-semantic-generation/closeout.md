# Closeout: Retry Degraded Semantic Generation

## Implemented scope

- Diagnosed the final `kis-dev` commissioning failure as persisted degraded semantic evidence, not a live Serena runtime failure.
- A matching generation with `semantic.status=degraded` was reusable because its provider/source/settings fingerprints remained current after Serena recovered.
- Discover now retries a degraded persisted semantic generation whenever a non-null semantic provider is configured; ready and null-provider generations retain ordinary reuse.
- The existing refresh/write/supersession path remains authoritative; no persistence schema or provider contract changed.

## Validation evidence

- RED regression: second read reused `degraded` instead of calling the recovered provider.
- GREEN regression: second read refreshed to `ready`; third read reused the recovered generation; provider called exactly twice.
- Focused persistent-intelligence/Discover suite: 24/24 passed.
- Governed scope check: only declared 090 paths.
- Canonical `scripts\verify.ps1`: pytest 100%, exit 0, two expected skips, 246 Python files, 81 governance claims, all configuration/interpreter/dependency/syntax/line-ending checks passed.

## Review

- The change preserves deterministic fallback, provider fingerprints, evidence schema, recoverable supersession, and HR-001/HR-002/HR-003.
- Trade-off: a persistently degraded configured semantic provider is retried on subsequent reads rather than cached indefinitely; this is intentional recovery behavior.
- No blocking findings remain before integration.

## Git and merge

- Branch: `change/090-retry-degraded-semantic-generation`.
- Worktree: `.work/worktrees/090-retry-degraded-semantic-generation`.
- Implementation checkpoint, integration, final live commissioning, exact publication, and governed cleanup remain pending.

## Required final commissioning

- Fast-forward the verified 090 checkpoint into clean primary `main`.
- Restart `kis-dev` from that integrated head.
- Call `inspect_project` against the existing degraded persisted generation and prove it refreshes to Serena `ready`, then prove the next call reuses that recovered generation.
- Re-run provider live smoke, GitHub Project preview, registered GitHub exact publication verification, Work/HR-003 smoke, and clean-state audit.
- Run a final canonical verifier on the exact closeout head before publishing and governed cleanup.
