# Serena Capability Boundary Implementation Plan

**Goal:** Close issue #408 without changing generic capability semantics or broadening Serena authority.

**Architecture:** Keep Serena's upstream runtime discovery for provider internals, but expose a separate fail-closed public runtime-tool projection filtered to the descriptor's approved three read operations. Feed only that projection into generic provider runtime augmentation so search and dispatch never learn unexpected upstream operations.

**Tech Stack:** Python, FastMCP provider/capability contracts, pytest, PowerShell change governance.

## Global constraints

- Stay inside `scope.json`; no #403, #407, or #395 paths.
- Preserve exactly the three approved public Serena reads and offline startup.
- Treat upstream tool metadata as untrusted; unknown names are ignored, not inferred.
- Add adversarial tests before implementation and retain red/green evidence.

### Task 1: Boundary TDD

- Inject approved plus mutation/admin/shell Serena metadata into the runtime snapshot.
- Prove current runtime projection/catalogue/search includes forbidden operations.
- Prove current generic dispatch can reach a leaked callable.

### Task 2: Serena-local projection fix

- Add an exact public runtime-tool projection to `SerenaRuntimeAdapter`.
- Bind the provider descriptor's runtime probe to that projection.
- Leave generic provider/capability augmentation unchanged.

### Task 3: Verification and closeout

- Run focused provider/capability regression tests and affected broader tests.
- Run diff hygiene, governed change checks, and independent security/API review.
- Publish a reviewable exact head, require canonical GitHub Actions on that head, and complete governed closeout only from matching evidence.
