# Tasks

- [x] Reproduce the receipt overwrite failure under `powershell.exe` with a focused regression test.
- [x] Implement compatible atomic receipt replacement for primary and fallback receipts.
- [x] Pass focused post-land restart tests.
- [x] Pass governed scope/check validation.
- [ ] Review and publish the exact change.
- [ ] Land only after exact-head CI and Work merge-readiness pass.
- [ ] Live-trigger the landed hook and prove `kis-dev` 8011 restart plus healthy `state=launching` receipt with exact landed/launched SHA evidence.
- [ ] Complete Work #469 and clean Change 233.
