# Change Specification: Codex Fingerprint Stability

- **Change ID**: `158-codex-fingerprint-stability`
- **Status**: Active
- **Complexity**: Medium
- **Risk triggers**: None

## Outcome

Fix #261 by making Codex read-only repository fingerprinting stable for pre-existing dirty diffs while preserving fail-closed mutation detection.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`, GitHub issue #261.
- Owned paths: `scripts/invoke-codex-agent.ps1`, `tests/tools/codex_cli/test_adapter.py`, this change record.
- Shared paths: none.
- Excluded paths: reviewer orchestration, NVIDIA backend, policy, provider/runtime composition, unrelated active changes.
- Dependencies: current `main` at `4e107b660a9925569d32eb19927b361da7149de5`.

## Requirements

- **R1 — Stable state evidence**: repository fingerprinting must hash successful Git state output only; diagnostic stderr must not become repository-state evidence.
- **R2 — Dirty-tree correctness**: a pre-existing tracked working-tree diff must survive a no-op Codex invocation without `CODEX_CLI_MUTATION_DETECTED`.
- **R3 — Fail closed**: any actual repository-state mutation during the invocation must still return exit code 86 and `CODEX_CLI_MUTATION_DETECTED`.
- **R4 — Read-only execution unchanged**: keep the existing ephemeral, JSON, read-only Codex execution contract and typed Git command failures.

## Acceptance

1. A synthetic repository with an intentional dirty tracked diff and a no-op fake Codex CLI exits 0 and preserves the exact diff.
2. A fake Codex CLI that changes repository content still exits 86 with `CODEX_CLI_MUTATION_DETECTED`.
3. Focused Codex adapter/wrapper tests pass on the current change.
4. Required code-quality review reports no blocking findings.

## Risks and recovery

- Risk: suppressing diagnostic stderr could hide a Git warning that is actually state-relevant.
- Mitigation: only successful command stdout is fingerprint evidence; every non-zero Git exit still throws its existing typed failure.
- Recovery: revert the bounded wrapper/test commit; no persistent data or migration is involved.

## Out of scope

- Changing the fingerprint state dimensions (HEAD, status, tracked diff, untracked content hashes).
- Weakening or removing mutation detection.
- Changing Codex authentication, sandbox level, reviewer prompts, fallback behavior, or NVIDIA review behavior.
- Fixing unrelated #265, #273, #274, #270, or #241 work.
