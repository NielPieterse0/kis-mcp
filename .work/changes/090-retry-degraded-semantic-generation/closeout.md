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
- Implementation checkpoint: `0e2192ca7e6bddacd2b61a204d33aab776b6d6f9`.
- Integrated by fast-forward into local primary `main` at the same SHA before live commissioning.

## Live commissioning

- Fresh `kis-dev` reached `ready` from integrated primary `main` on `127.0.0.1:8011`.
- First identical `inspect_project` call refreshed the previously degraded generation to Serena 1.6.1 `available=true`, with no `SEMANTIC_PROVIDER_UNAVAILABLE` unknown.
- Second identical call returned `persistence.status=reused` with the same recovered generation ID, proving normal warm reuse after recovery.
- Provider live smoke passed: Context7 local startup/tool discovery; Serena offline semantic reads; memory quarantine/restore; restart verification; `repo_local_state_absent=true`.
- GitHub Project issue #102 reconciliation preview remained `noop`, `success=true`, `Status=Done`.
- Work write/read passed; direct permanent-delete intent returned `HR-003_QUARANTINE_REQUIRED`; the marker was recoverably quarantined as `20260810T081416981766Z-e811ef09e174`.

## Post-closeout procedure

- Fast-forward this metadata-only closeout commit into `main`.
- Run canonical `scripts\\verify.ps1` on that exact primary head.
- Publish only that verified SHA through the registered-GitHub exact operation using the observed remote `main` SHA as the expected base.
- Independently verify GitHub `main`, reconcile local `origin/main`, and run governed cleanup for 090 without force deletion.
- Restart `kis-dev` from the exact published head and repeat health plus Discover semantic recovery/reuse checks before declaring commissioning complete.
