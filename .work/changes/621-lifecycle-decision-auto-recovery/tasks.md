# Tasks: Lifecycle Decision Auto Recovery

- [x] Recover and verify `kis-op` before touching `kis-dev`.
- [x] Add #650 to Work, complete triage metadata, and claim it Active.
- [x] Record the operator-approved dual-runtime auto-recovery scope on #650.
- [x] Create isolated governed Change 621 from clean `main` at `e29b8612...`.
- [x] Confirm authority, current PromotionReady/evidence architecture, runtime launcher, and active path claims.
- [x] Add failing lifecycle decision / redundant-verification / stale-closeout tests.
- [x] Implement lifecycle decision and guard surfaces without duplicating existing lifecycle truth.
- [x] Add failing generalized recovery / health hook / peer-isolation tests.
- [x] Implement generalized local-shell recovery for both instances and post-land delegation, including retry/backoff after transient restart failure.
- [x] Reconcile product and Operations documentation.
- [x] Run focused affected verification and required specialist reviews; architecture review passed, code-quality projection required exact-diff/manual fallback, and safety reviewer infrastructure returned 502.
- [x] Run `pwsh -File scripts/change-workflow.ps1 check`; stale completed Change 618 was safely cleaned after it blocked admission with an obsolete exclusive path claim.
- [ ] Prepare reviewable PR; use exact-head GitHub Actions as canonical full verification.
- [ ] Pass merge readiness, merge exact approved head, and run post-merge commissioning.
- [ ] Reconcile documentation/Work completion, close #650, and safely clean Change 621.
- [ ] Verify clean `main`, exact GitHub truth, and both KIS runtimes healthy.
