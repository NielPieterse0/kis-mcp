# Closeout: Issue Close Readback and kis-dev Post-Land Restart

## Implemented scope

- Commissioning issue close now treats `github_issue_write` as acknowledgement and confirms the exact issue number plus `state=closed` through `github_issue_read`.
- Direct PR merge and merge-queue land emit one provider-neutral landed event to the same injected runtime dispatcher; existing schema-version-1 landing result key sets remain unchanged.
- Direct merge requires GitHub `mergeCommit.oid` as the exact landed identity and does not substitute the PR head or a branch-head read-back; merge-queue `land_with_identity` separately proves the landed candidate equals the advanced queue base before the dispatcher can schedule. If exact landed identity is unavailable, restart is skipped and bounded failure evidence is retained without changing landing truth.
- The scheduler can bootstrap the worker script from the currently executing source artifact when pre-land primary `main` does not yet contain it; the detached worker receives primary `RepositoryRoot` explicitly, requires clean `main`, verified fetch, fast-forward-only synchronization, containment of the required landed reference, and then invokes only the synchronized primary `scripts/start-chatgpt.ps1 kis-dev`.
- Scheduler and worker failures retain bounded atomic latest-state evidence beneath `C:\Projects\.kis-mcp`; worker receipts record both the triggering `landed_sha` and actual synchronized `launched_sha`, and no reset/force path exists.
- `SPEC.md` and `docs/operations/chatgpt-remote.md` own the durable implementation and operator statements.

## Validation evidence

- Red/green commissioning regression reproduced the provider `{id,url}` close-write response and now passes with authoritative read-back.
- Affected commissioning, exact-merge, merge-queue, and post-land restart tests pass on the current implementation.
- The isolated PowerShell worker behavioral test uses fake Git/GitHub boundaries and records exactly one restart target: `kis-dev`.
- PowerShell syntax parsing, `git diff --check`, and the governed final scope check pass; canonical repository verification is rerun before publication.

## Review

- Earlier code-quality, architecture, API-contract, and test-quality findings were remediated, including non-interfering post-land failure evidence, neutral runtime composition, internal landed-identity proof, unchanged schema-version-1 success shapes, and explicit failure/recovery coverage.
- Automated architecture and documentation review are clean on the final source implementation lineage.
- On source fingerprint `eb3bde20fa7f07f180a4c64081872036d80311f5022ed49eb9ca7a13e40d2de6`, the code-quality, API-contract, and test-quality evidence projectors could not include the complete changed-test set and therefore required their mandated exact-diff manual fallback.
- Those exact-diff fallbacks reviewed the complete production/test delta, including authoritative issue close write/read ordering and resumability, direct/queue public success contracts, internal queue landed identity, runtime-owned post-land failure evidence, scheduler/worker validation, and negative dispatch paths; no remaining publication blocker was found.

## Delivery and live verification

- Publication, exact-head GitHub Actions, Work Management merge-readiness, merge, and cleanup remain pending.
- The landed revision must demonstrate the automatic post-land path on `kis-dev`; `kis-op` is not a restart/stop target for this change.
- Commissioning #462 remains pending final resume from its persisted checkpoint after the landed runtime is current.

## Recovery and residual risk

- An irreversible GitHub landing remains authoritative even when the later development restart path fails.
- Restart failures leave the prior development runtime and local Git state unre-written and retain failure evidence for supervised recovery.
- The worker relies on the existing selected-instance launcher for safe `kis-dev` reclaim and unrelated-listener refusal.
