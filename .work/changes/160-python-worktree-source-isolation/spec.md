# Change Specification: Python Worktree Source Isolation

- **Change ID**: `160-python-worktree-source-isolation`
- **Status**: Active
- **Complexity**: Medium
- **Risk Triggers**: `architecture_boundary`, `public_contract`
- **Work Item**: `kis-mcp` issue #265 / `DEFECT-265`

## Outcome

Bind KIS-launched repository/worktree processes to the selected worktree Python source so a shared or repo-root virtualenv with editable metadata pointing at another checkout cannot silently execute/import that other checkout.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, issue #265, research handoff #272, state-ownership slice #278.
- Owned production paths: `src/kis_mcp/process_environment.py`, `src/kis_mcp/middleware.py`, `src/kis_mcp/gateway/composition.py`, `src/kis_mcp/workflows/verification/execution.py`.
- Owned tests: `tests/test_process_environment.py`, `tests/workflows/verification/test_verification_execution.py`.
- No shared paths. Do not touch active #241, #261, #270, #274, #278 implementation paths.

## Requirements

- **REQ-001 — Source selection:** For a KIS-launched process whose effective shell working directory resolves inside a registered Git checkout/worktree with a `src` directory, derive that checkout/worktree's `src` path as the authoritative Python source root.
- **REQ-002 — Process-local isolation:** Prepend the authoritative source root to `PYTHONPATH` for the launched process only. Do not edit, reinstall, or otherwise mutate the selected virtualenv.
- **REQ-003 — Generic boundary:** Apply source binding at the generic Desktop Commander process-launch boundary, not only inside verification.
- **REQ-004 — Fail closed on ambiguity:** If one command would execute from multiple distinct registered source checkouts, or source binding is required but cannot be rendered safely for the selected shell, reject the call with a non-HR typed process-source error instead of producing ambiguous execution evidence.
- **REQ-005 — Preserve non-applicable execution:** Leave commands outside registered Git checkouts and registered projects without a `src` source root unchanged. Explicit external interpreters remain usable; when launched from a selected registered checkout they receive that checkout source through process-local `PYTHONPATH`.
- **REQ-006 — Verification reconciliation:** Remove the verification-only `PYTHONPATH` injection so verification consumes the same generic process-source contract as ordinary process execution.
- **REQ-007 — Idempotent intent:** Reject commands that explicitly rewrite `PYTHONPATH` after KIS would bind a registered source root because their final source identity cannot be guaranteed safely.

## Acceptance

1. **Given** a registered worktree with package source under `worktree/src` and a shared Python environment whose editable-path metadata resolves the same package to root `main/src`, **when** KIS launches Python after selecting the worktree, **then** the imported package comes from the worktree.
2. **Given** an applicable PowerShell or cmd process launch, **when** KIS normalizes the call, **then** the selected checkout `src` is first in process-local `PYTHONPATH` and the virtualenv is not mutated.
3. **Given** a command that traverses two distinct registered worktrees, **when** KIS cannot establish one source identity for the process, **then** it fails with an explicit process-source ambiguity error.
4. **Given** a registered-source command that explicitly rewrites `PYTHONPATH`, **when** KIS cannot guarantee source precedence, **then** it fails explicitly rather than claiming isolated execution.
5. **Given** a command outside a registered source-bearing checkout, **when** KIS normalizes it, **then** arguments are unchanged.
6. **Given** `run_verification`, **when** it constructs its nested process command, **then** it selects the project directory but contains no verification-specific source-binding implementation; the generic middleware owns that behavior.

## Risks and recovery

- **Risk:** shell rewriting changes user-visible process semantics. Mitigation: only source-bearing registered checkouts are modified; support PowerShell/cmd explicitly and reject unsafe ambiguity.
- **Risk:** source selection could bind the registered project root instead of a linked worktree. Mitigation: resolve the nearest `.git` marker from each effective command cwd before constructing the source root.
- **Risk:** later #278 state-ownership work could duplicate source identity rules. Mitigation: record the resulting rule as a handoff on #278; do not add competing persistent state.
- **Recovery:** revert change `160-python-worktree-source-isolation`; no virtualenv or persistent external state is mutated.

## Out of scope

- Moving KIS state directories or implementing #278 state namespaces.
- Changing virtualenv contents, editable-install metadata, dependency resolution, or Python packaging.
- Fixing #261, #273, #274, #270, #241, or unrelated process policy.
- Adding a new HR policy rule or changing Desktop Commander provider schema.
