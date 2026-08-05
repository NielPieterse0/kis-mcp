# 035 LLM Capability Specification

## Outcome

Add two optional inference capabilities to kis-mcp and expose them through one advisory code-review agent:

- NVIDIA NIM through an OpenAI-compatible HTTPS API endpoint.
- Codex CLI through a fixed PowerShell wrapper and non-interactive read-only execution.

## Architecture

- `providers/nvidia` owns NVIDIA configuration, readiness, HTTP transport, response parsing, and provider registration.
- `tools/codex_cli` owns only the Codex-specific adapter and descriptor, registers through the generic `kis_mcp.tools` framework delivered by change `029-tools-code-tooling`, and invokes `scripts/invoke-codex-agent.ps1`.
- `workflows/code_review` owns one `code-reviewer` role, bounded repository evidence collection, backend selection/fallback, normalization, and FastMCP tool registration.
- This change coexists with `029-tools-code-tooling`: 029 owns the generic Tools framework and explicitly excludes `tools/codex_cli/**`, while this slice owns only that excluded Codex adapter path.
- The agent surface is separate from ordinary Desktop Commander Work forwarding. It does not alter HR-001, HR-002, or HR-003.

## Configuration

All non-secret configuration is JSON in `settings/agents/code-review-agent.settings.json` and validated against a checked-in schema. Secrets remain process environment values. NVIDIA uses `NVIDIA_API_KEY`; Codex uses the CLI's existing supervised authentication state.

## Public operation

Expose one additive tool:

`review_change_with_agent(path, instructions="", backend=None)`

The operation reviews the current Git working-tree change under one repository path. `backend` may be `nvidia-nim` or `codex-cli`; when omitted, configured preferred/fallback order applies.

## Boundaries

- One agent role only: `code-reviewer`.
- Delegation depth is exactly one; no sub-agent spawning.
- Advisory output only; no edits, commits, merges, or destructive actions.
- Codex is invoked with an ephemeral, non-interactive, read-only profile and a before/after Git-visible repository fingerprint check.
- NVIDIA receives bounded local evidence only.
- Provider/tool failure does not prevent gateway startup.
- Credentials and raw authorization values are never returned, logged, or stored in JSON.

## Acceptance criteria

1. NVIDIA settings and readiness distinguish disabled, missing key, and ready states.
2. NVIDIA requests use the configured OpenAI-compatible chat-completions endpoint, bearer authentication, timeout, model, temperature, and output budget.
3. Codex adapter invokes the fixed PowerShell script through the generic Tools registry, supplies the prompt through stdin, parses JSONL agent output, reports timeout/process/protocol failures, and rejects detected Git-visible repository mutation.
4. The code-review agent gathers bounded AGENTS/status/diff evidence, selects one backend, uses fallback only after an unavailable or failed preferred backend, and normalizes structured or unstructured output.
5. `build_server()` registers exactly one new agent tool without reducing existing tools.
6. Focused tests and full `scripts/verify.ps1` pass.
7. The branch is reviewed, merged through a PR, and its worktree/branches are cleaned without force.
