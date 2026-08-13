# Change Specification: DB/Docker Commissioning Hardening

- **Change ID**: `111-db-docker-commissioning-hardening`
- **Status**: Approved for implementation by the operator commissioning request
- **Risk Profile**: standard
- **Development level**: Medium — bounded code/docs change with external-provider runtime evidence and rollback needs.

## Outcome

Complete safe commissioning of the change-109 DBHub and Docker Hub providers without modifying third-party pinned bytes or weakening KIS policy.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`.
- Owned implementation: Docker Hub public tool allowlist and commissioning wrapper only.
- Owned verification: `tests/providers/test_dbhub_dockerhub_integration.py` plus live commissioning evidence.
- Owned documentation: current implementation truth in `SPEC.md`; commissioning/runbook truth in `docs/OPERATIONS.md`.

## Requirements

- **REQ-001**: Keep DBHub pinned at `v1.2.0` / `1bed0b8...a0b0` and Docker Hub pinned at `ad806e2...65c2`.
- **REQ-002**: Expose only Docker Hub public operations proven usable in current live commissioning; exclude `search` while its upstream result violates its declared output schema.
- **REQ-003**: Preserve public/read-only Docker Hub mode; do not add PATs, mutations, Docker Engine authority, or Work network access.
- **REQ-004**: Treat provider stderr logging as diagnostic output, not a commissioning failure when the child process exits successfully.
- **REQ-005**: Record exact live evidence and residual dependency/security risk without overstating commissioning.

## Acceptance

1. DBHub live stdio discovery exposes `college_results_search_objects` and `college_results_execute_sql`, and `SELECT 1 AS commissioned` returns `1` from the College SQLite binding.
2. Docker Hub live calls succeed for `checkRepository`, `checkRepositoryTag`, `getRepositoryInfo`, `getRepositoryTag`, `listRepositoriesByNamespace`, and `listRepositoryTags` in public mode.
3. Docker Hub `search` is absent from the KIS public surface while the pinned upstream server rejects current Docker Hub `search_after` responses.
4. `commission-db-docker-providers.ps1` exits zero when both provider sessions are live even if providers write ordinary diagnostics to stderr.
5. Focused tests, change-workflow check, canonical verification, and post-restart provider status are green.

## Risks and recovery

- Residual risk: the pinned Docker Hub dependency tree currently reports 13 production advisories (0 critical, 9 high); KIS constrains it to single-client stdio and public read operations only.
- Recovery: revert change 111; provider installations and the earlier partial copy remain recoverable beneath `C:\Projects\.kis-mcp\quarantine`.

## Out of scope

- Upgrading either third-party provider pin.
- Patching third-party installed bytes or falsifying source identity.
- PAT-authenticated Docker Hub mutations or local Docker Engine operations.
