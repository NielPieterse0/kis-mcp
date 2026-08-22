# Tasks: Issue Close Readback and kis-dev Post-Land Restart

- [x] Add failing commissioning regression for narrow close-write response.
- [x] Implement authoritative `github_issue_read` close confirmation.
- [x] Add negative close-readback coverage.
- [x] Add scheduler/worker tests for `kis-mcp/main`, fast-forward-only sync, detached launch, and behavioral `kis-dev`-only targeting.
- [x] Implement post-land scheduler and PowerShell worker.
- [x] Bind scheduler after verified direct merge without changing the public result schema.
- [x] Bind scheduler after verified merge-queue landing with explicit landed-identity proof.
- [x] Update current product and ChatGPT remote operations documentation.
- [x] Run focused affected test suites.
- [x] Run governed scope check on the final diff.
- [x] Run required specialist reviews and remediate findings on the final inspected implementation; architecture/documentation complete automatically, while code-quality/API-contract/test-quality use mandated exact-diff manual fallback on source fingerprint `eb3bde20fa7f07f180a4c64081872036d80311f5022ed49eb9ca7a13e40d2de6` because their bounded evidence projectors omit changed-test evidence.
- [ ] Publish and obtain exact-head CI plus merge-readiness.
- [ ] Merge, verify local `main`, and verify automatic `kis-dev` replacement only.
- [ ] Resume commissioning #462 to terminal state without lifecycle-managing `kis-op`.
