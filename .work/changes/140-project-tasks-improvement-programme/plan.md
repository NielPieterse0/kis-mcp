# Plan: Project Tasks Improvement Programme

## Delivery order

1. **#216 Runtime generation identity**
   - Extend launcher ready-state evidence.
   - Validate generation in gateway status projection.
   - Add stale-generation/init regression tests.
2. **#217 Current/resume workflow**
   - Add typed current-work selection in Work Management.
   - Add service and MCP read-only operation.
   - Cover none/one/multiple/truncated cases.
3. **#218 Board projection / Control Center**
   - Add typed normalized board projection.
   - Add service/MCP board read.
   - Inject board source into Control Center snapshot and render fallback.
4. **#219 Contract hardening**
   - Add shared operational result envelope and typed error classification.
   - Apply accurate read/mutation tool annotations.
   - Preserve compatibility and explicit apply/idempotency semantics.
5. Reconcile `SPEC.md` and `docs/OPERATIONS.md`.
6. Run exact-head GitHub canonical verification and required architecture/API/code-quality reviews available through provider evidence.
7. Fix all blocking findings, merge exact verified head, then reconcile #216–#219 and #215 to actual delivery/commissioning state.

## Concurrency control

Do not modify EvidenceStore, project registry/identity, or `.temp/kis` capsule implementation while change 136 is active. If implementation discovery requires those paths, defer that portion rather than overlap the unpublished claim.

## Verification strategy

- Focused unit tests for each slice in CI-capable repository test files.
- Existing tests preserved.
- `git diff --check` / canonical repository verification on exact PR head through GitHub Actions.
- Specialist reviews required by classification: code-quality, architecture, api-contracts; deployment/persistent-state evidence covered by focused tests and canonical verification.
- Live KIS runtime commissioning is a separate post-merge evidence gate when the host can invoke `kis-dev`/`kis-op`; do not fake it.
