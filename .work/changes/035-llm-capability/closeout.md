# Closeout: NVIDIA NIM and Codex Code-Review Agent

## Implemented

- Added strict JSON settings and schema for one optional `code-reviewer` agent.
- Added an NVIDIA NIM provider using the hosted OpenAI-compatible chat-completions endpoint and `NVIDIA_API_KEY` environment reference.
- Added a Codex CLI adapter behind the generic Tools registry and fixed PowerShell wrapper.
- Added one additive `review_change_with_agent` workflow with bounded local evidence, one fallback, normalized advisory output, and no nested delegation.
- Added Codex before/after Git-visible repository fingerprinting and `CODEX_CLI_MUTATION_DETECTED` handling.
- Preserved the existing `build_server()` public signature and contained missing or invalid optional agent settings.

## Review

- No blocking scope, policy, secret, credential, provider-runtime, public-contract, fallback, or dependency-direction findings remain.
- NVIDIA is catalogued for workflow use and is not mounted as a general provider passthrough.
- Codex is a local executable Tool descriptor whose invocation has an explicit external-network effect and remains optional.
- The implementation does not add a fourth policy rule or modify HR-001, HR-002, or HR-003.

## Verification

- Focused command: `.work/changes/035-llm-capability/run-focused-tests.ps1` — 34 passed.
- PowerShell parser accepted `scripts/invoke-codex-agent.ps1` without syntax errors.
- Settings and schema JSON parse successfully.
- `change-workflow.ps1 validate` and `check` passed with all changed paths inside 035 ownership.
- Full `scripts/verify.ps1` passed after integrating current `origin/main`: 125 Python files compiled, full pytest passed with two expected skips, and line-ending, configuration, interpreter, dependency, governance, and exact three-rule checks passed.

## Commissioning state

- NVIDIA endpoint/model configuration is implemented, but this process has no `NVIDIA_API_KEY`; live inference is not claimed.
- Codex invocation is implemented, but `codex` is not currently on PATH; live Codex authentication or review is not claimed.
- PowerShell is present and the wrapper was executed successfully in tests against temporary non-mutating and mutating fake Codex executables.

## Recovery

Before merge, abandon the unmerged branch and remove the clean worktree normally. After merge, revert the merge commit if rollback is required. No persistent schema, credential, installation, or secret migration is introduced.

## Git and merge

- Branch: `change/035-llm-capability`.
- Implementation commit: `5948e45`.
- Verified integration head before this closeout record: `62ce7aae234cf7dc8bb3fc78e2529322be45f567`.
- Pull request: `#48 — Add NVIDIA NIM and Codex code-review agent`.
- PR file review found exactly the 34 declared paths; GitHub has no configured check runs for this head.
- Merge method: merge commit at the exact final verified closeout head.
- Cleanup: run immediately after merge through `change-workflow.ps1 cleanup 035-llm-capability`, then remove the remote branch without force.
