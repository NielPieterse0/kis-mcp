# Change: README Navigation

- **Change ID**: `168-readme-navigation`
- **Repository complexity**: `small`
- **Documentation level**: `Small`
- **Risk triggers**: none

## Outcome

Keep `README.md` as a concise human landing page by removing volatile capability/current-state projections and duplicated operator procedure while routing detail to canonical owners.

## Authority and scope

- `AGENTS.md` owns documentation routing and declares `README.md` human orientation/navigation only.
- `SPEC.md` owns current product architecture/status.
- `docs/OPERATIONS.md` and `docs/operations/**` own operator procedure.
- Only `README.md` plus this change record may change.

## Plan and acceptance

1. Remove the volatile Current capability summary.
2. Keep product orientation, authority/navigation, repository layout, and concise development/verification entry points.
3. Replace duplicated bootstrap/startup/verification procedure with links to the canonical Operations index where practical.
4. Preserve valid repository-relative links and tested README expectations.
5. Run focused documentation/repository checks, review the exact change, then publish through exact-head PR verification.