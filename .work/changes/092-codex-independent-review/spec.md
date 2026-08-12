# Change Specification: Codex Independent Review

- **Change ID**: `092-codex-independent-review`
- **Status**: Approved for implementation by the operator request and the explicit 091 follow-up boundary
- **Development Level**: Complex
- **Risk Profile**: rigorous

## Outcome

Commission a pinned local Codex CLI authenticated with the operator's ChatGPT subscription as an explicitly selectable, advisory reviewer for both code quality and safety/security, while removing interactive vault-unlock prompts from ordinary KIS startup. Operator unlock input remains required for vault initialization, secret mutation, master-key rotation, and one-time migration of an existing vault to the runtime credential.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`, and the closed 091 follow-up requirement.
- External Codex authority: OpenAI Help/official `openai/codex` repository. Stable CLI pin: `0.147.0` released 2026-08-07; alpha releases are excluded.
- Owned paths: exactly those declared by `scope.json`.
- Shared paths: none.
- Excluded paths: `policy/**`.
- Dependencies: existing Tools registry, code-review workflow, Windows Credential Manager helper, encrypted application vault, selected-instance launcher.
- Integration owner: this change.

## Architecture

1. **Codex installation/authentication**: add a JSON-pinned bootstrap definition for `@openai/codex@0.147.0`, install beneath `C:\Projects\.kis-mcp\tools\codex\0.147.0`, and use a managed `CODEX_HOME` beneath `C:\Projects\.kis-mcp\agent-hosts\codex-reviewer`. Authentication uses Codex's interactive **Sign in with ChatGPT** flow; no OpenAI API key is configured in KIS.
2. **Review roles**: retain one `CodeReviewAgent` and one public review operation. Add strict `review_type=code-quality|safety-security`. Explicit `backend=codex-cli` remains non-fallback and therefore independent from NVIDIA. Prompts are purpose-specific, evidence-bounded, advisory, and require concrete evidence for findings.
3. **Codex execution boundary**: retain `codex exec --ephemeral --json --sandbox read-only`, prompt over stdin, managed `CODEX_HOME`, and before/after Git-visible repository fingerprinting. No mutation, nested delegation, commit, merge, or destructive action is authorized.
4. **Runtime vault unlock**: the encrypted vault remains AES-256-GCM/Argon2id. A verified vault unlock is stored once in Windows Credential Manager under a non-secret target named in `settings/secrets.settings.json`. Ordinary `start-chatgpt.ps1` reads that credential non-interactively solely to resolve required vault references, then clears transient variables. Vault initialization and rotation synchronize the credential only after successful cryptographic operations; existing vaults use one explicit migration command.
5. **Policy invariance**: no fourth Work rule is introduced. Codex/NVIDIA review remains an explicit advisory external-capability path and does not alter HR-001, HR-002, or HR-003.

## Requirements

- **REQ-001 — Stable Codex pin**: bootstrap configuration pins `@openai/codex` exactly to stable version `0.147.0`; no `latest`, alpha, or implicit upgrade is used.
- **REQ-002 — Project-contained Codex state**: installation, npm cache, and `CODEX_HOME` used by KIS remain under `C:\Projects`.
- **REQ-003 — ChatGPT subscription authentication**: Codex authentication is performed through its interactive ChatGPT sign-in flow and KIS stores no OpenAI API key for Codex.
- **REQ-004 — Version-aware readiness**: Codex readiness distinguishes disabled, missing executable, version mismatch, unverified authentication, and ready/commissioned runtime states without exposing credentials.
- **REQ-005 — Independent backend selection**: `backend=codex-cli` invokes only Codex and never silently falls back to NVIDIA.
- **REQ-006 — Two strict review purposes**: `review_type` accepts exactly `code-quality` and `safety-security`; invalid values return a structural invalid request before any backend call.
- **REQ-007 — Code-quality prompt**: code-quality review focuses on correctness, regressions, error handling, tests, maintainability, and stated requirements, with evidence-backed findings only.
- **REQ-008 — Safety/security prompt**: safety/security review focuses on secrets, authentication/authorization, trust boundaries, injection/command execution, network/filesystem effects, data handling, race/TOCTOU, dependency/supply-chain risk, and policy bypass where supported by evidence.
- **REQ-009 — Read-only Codex containment**: Codex runs ephemeral/read-only and any Git-visible mutation causes bounded failure code `CODEX_CLI_MUTATION_DETECTED`.
- **REQ-010 — Runtime secret credential setting**: `settings/secrets.settings.json` declares the Windows Credential Manager target; no credential value or derived key is stored in repository JSON.
- **REQ-011 — Startup is non-interactive**: ordinary `start-chatgpt.ps1` must not call `Read-Host`/`Get-KisMcpUnlockPayload`; it resolves NVIDIA through the verified runtime credential and fails closed with actionable setup guidance when that credential is missing/invalid.
- **REQ-012 — Mutation remains interactive**: `set-secret.ps1`, vault initialization, and rotation continue requiring operator unlock input unless the explicit bootstrap environment is intentionally supplied.
- **REQ-013 — Runtime credential synchronization**: successful vault initialization stores the supplied unlock for runtime use; successful rotation updates it to the new unlock only after the vault rotation succeeds.
- **REQ-014 — Existing-vault migration**: one explicit command verifies the operator-supplied existing unlock before storing it as the runtime credential; wrong unlock never changes Windows credential state.
- **REQ-015 — Secret containment**: unlock material, NVIDIA keys, Codex auth tokens, and credential values never appear in command arguments, JSON settings, MCP output, startup state, retained logs, Git diff, or error text.
- **REQ-016 — Backward compatibility**: existing NVIDIA profile/default/fallback behavior and `review_change_with_agent` callers without `review_type` continue to work, defaulting to `code-quality`.
- **REQ-017 — Policy invariance**: HR-001/HR-002/HR-003 remain byte-for-byte unchanged.
- **REQ-018 — Commissioning**: focused tests and full verification pass; the exact candidate/final head proves Codex CLI version/authenticated review for both purposes when local bootstrap/sign-in can be completed, and proves startup no longer requests the vault unlock.

## Acceptance

1. Given bootstrap settings, when inspected, then Codex is pinned to `0.147.0` and every writable path is beneath `C:\Projects`.
2. Given Codex is absent or wrong-version, when readiness is requested, then the state is degraded with non-secret remediation details.
3. Given an authenticated pinned Codex CLI, when `review_change_with_agent(..., backend="codex-cli", review_type="code-quality")` runs, then only Codex is invoked and returns normalized advisory findings.
4. Given the same backend with `review_type="safety-security"`, then the prompt contains the safety/security criteria and only Codex is invoked.
5. Given an invalid `review_type`, then no evidence/backend call occurs and the result is `invalid_request`.
6. Given ordinary KIS startup with the configured runtime unlock credential, then no interactive vault prompt occurs and NVIDIA receives its process-scoped key exactly as before.
7. Given the runtime credential is missing or invalid, then startup fails closed without leaking unlock material and names the explicit migration/setup command.
8. Given an existing vault and correct unlock, when the migration command runs, then unlock is cryptographically verified before Windows Credential Manager is updated.
9. Given a vault rotation, when rotation succeeds, then the runtime credential is updated to the new unlock; if rotation fails, the credential is unchanged.
10. Given final exact-head verification, then focused tests, `change-workflow check/validate`, `scripts/verify.ps1`, secret-redaction checks, and policy invariants pass.

## Risks and recovery

- **Credential persistence risk**: a same-user process may access Windows Credential Manager. This matches the existing single-operator Windows trust boundary and is preferable to plaintext files or startup prompts; no cross-user or machine-global secret is introduced.
- **Codex upstream drift**: exact stable pin plus version-aware readiness prevents silent upgrade drift. Updating Codex is a later explicit JSON/version change.
- **Codex Windows behavior**: managed `CODEX_HOME`, fixed wrapper arguments, read-only sandbox, and repository fingerprinting limit state/mutation risk.
- **Authentication interaction**: first ChatGPT sign-in requires operator browser/terminal interaction. If the governed Work path blocks bootstrap network, installation/auth is completed by the explicit supervised bootstrap script from a local terminal and then KIS performs read-only commissioning.
- **Recovery**: revert the change for repository behavior; remove/replace only the scoped Codex managed install/state or Windows runtime credential through explicit operator action. Never permanently delete repository artifacts through KIS.

## Out of scope

- OpenAI API-key based Codex authentication.
- Codex write/edit/auto/full-access modes.
- Nested Codex subagents or autonomous remediation.
- Changing NVIDIA model profiles or provider transport.
- Changing the three-rule policy.
- General-purpose persistent secret auto-unlock outside the current Windows single-operator trust boundary.
