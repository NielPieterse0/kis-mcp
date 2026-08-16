# Tasks: Disposable Windows Execution Foundation

- [x] Confirm repository authority, current GitHub `main`, and clean change base.
- [x] Capture roadmap issue `#324` and project it as Work Management `SPEC-324` (`Ready`, `Critical`, `Large`).
- [x] Create governed change `174-disposable-windows-execution-foundation` from exact verified `main`.
- [x] Record the full multi-slice roadmap and durable target-architecture placement.
- [x] Define first-slice requirements, acceptance criteria, risks, exclusions, and implementation plan.
- [x] Implement execution contracts/settings with tests first.
- [x] Preserve local-process verification through the new backend seam.
- [x] Implement and test one Hyper-V disposable execution proof path with recoverable guest retirement.
- [x] Move supervised live Hyper-V contract-parity commissioning and performance/network measurements to follow-up issue `#330`; current host lacks `Get-VMHost`, and this is no longer a merge-blocking acceptance criterion for change 174.
- [x] Run architecture and safety/security review gates; resolve blocking findings and record specialist-backend failures separately.
- [x] Run focused verification, scope check, diff check, and applicable local repository verification.
- [x] Publish the registered review branch and open PR `#329`; retain provider-native exact-head Actions as the landing gate. The current `windows-latest` job fails before runner assignment and is not implementation evidence.
- [x] Complete bounded `SPEC.md` current-product reconciliation after change 171 released the path through merged PR `#312`.
- [ ] Merge and safe cleanup after provider-native exact-head GitHub Actions succeeds; live Hyper-V commissioning continues independently in follow-up issue `#330`.
