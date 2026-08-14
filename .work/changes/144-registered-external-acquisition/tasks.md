# Tasks: Registered External Acquisition

- [x] Separate issue #214 from #215 / PR #221 and allocate governed change 144 / `SPEC-144`.
- [x] Inspect current `import-isolate` main and identify the missing KIS-facing recipe-safe bridge.
- [x] Register companion `import-isolate#2` and establish its test-first implementation branch/PR.
- [x] Add strict KIS authorization settings and result contract.
- [x] Implement registered-project/profile/recipe/hash/parameter authorization.
- [x] Implement bounded `import-isolate` host dispatch and strict result validation.
- [x] Add approval-gated `kis_acquire_registered_evidence` virtual capability.
- [x] Preserve registered-GitHub virtual approval/dispatch compatibility.
- [x] Add focused positive/negative/integration tests.
- [x] Review architecture, security, API contract, and exact diff; fix all blocking findings.
- [x] Land and verify the companion `import-isolate#2` provider boundary.
- [x] Reconcile durable KIS external-acquisition module documentation after #215 released shared documentation ownership.
- [x] Integrate current `main` exactly after #215 landed; verify zero overlapping files and use GitHub's two-parent synthetic merge tree.
- [ ] Run canonical KIS verification on the final integrated/documented reviewed head.
- [ ] Perform live allowed/denied provider commissioning from the landed interfaces when the required KIS/local containment runtime is available.
- [ ] Merge exact approved KIS head, refresh main, reconcile and close issue #214, and clean the change.
