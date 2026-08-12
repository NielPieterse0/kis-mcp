# Closeout: Documentation Authority Refresh

## Implemented scope

- Added the one-governed-fact / one-canonical-owner rule and explicit documentation routing to `AGENTS.md`.
- Reduced `README.md` to human orientation, current capability summary, quick start, repository navigation, and links to canonical detail; removed duplicated provider lifecycle, Discover, work-management, and configuration detail.
- Added explicit authority boundaries to `docs/TRUST-MODEL.md` and `docs/OPERATIONS.md`.
- Removed the competing file-by-file authority table from target-state `docs/PLATFORM-CONCEPT.md`; Govern now consumes the repository authority model from `AGENTS.md`.
- Corrected the stale `docs/OPERATIONS.md` Control Center statement: the read-only app is available through mounted `controlcenter_*` operations and as a standalone process.
- Added `RepositoryLineEndingNormalizer` as a narrow Work compatibility layer: `write_file` and `edit_block` newline-bearing text arguments are normalized to local Git's effective `text`/`eol` attributes before Desktop Commander forwarding; explicit CRLF and binary rules are preserved and Git remains the attribute parser.
- Wired the normalizer into gateway middleware without adding a provider, dependency, setting, filesystem implementation, or fourth policy decision.
- Left `SPEC.md`, the active 093 Discover scope, historical `.work/changes/**`, `docs/development/**`, `docs/STARTUP-HARDENING.md`, and `docs/LESSONS-APPLICABILITY.md` unchanged.

## Validation evidence

- `scripts/change-workflow.ps1 validate`: passed with three active non-overlapping changes (`093`, `094`, and `095`) after the later 095 slice registered during execution.
- `scripts/change-workflow.ps1 check`: passed after the expanded scope; changed paths remain limited to registered 094 ownership.
- TDD red evidence: `tests/test_line_endings.py` initially failed collection because `kis_mcp.line_endings` did not exist.
- Focused regression suite: 19 tests passed across `tests/test_line_endings.py`, `tests/test_middleware.py`, and `tests/capabilities/test_gateway_composition.py` after fixing the binary inherited-EOL edge case and Git-environment isolation.
- Canonical `scripts/verify.ps1` passed on the LF-normalized implementation state: repository line-ending policy clean with `core.autocrlf=false`, `core.eol=lf`, and `core.safecrlf=true`; full pytest exit `0` with two expected skips; 247 Python files syntax-checked; configuration, dependencies, change governance, and final service verification all passed.
- Contradiction search for `not mounted into the primary gateway`: no matches remain in the refreshed worktree documentation.
- Policy JSON, settings, contracts, provider package, and external dependencies are unchanged. Source changes are limited to the line-ending compatibility layer and its gateway wiring.

## Review

- Manual authority/code/diff review: no blocking finding after checking source-of-truth routing, current-vs-target boundaries, scope, current capability summaries, relative links, historical-record exclusions, binary/CRLF handling, Git worktree resolution, middleware argument replacement, and preservation of Desktop Commander as the filesystem writer.
- Configured independent Codex review was attempted and failed before findings with `AGENT_BACKEND_FAILED:CodexCliError`; no Codex pass is claimed.
- Configured NVIDIA NIM `super` review was attempted and failed before findings with `AGENT_BACKEND_FAILED:NvidiaNimError`; no NVIDIA pass is claimed.
- The advisory-backend failures do not change repository verification evidence; they remain a review-tool availability limitation for this bounded documentation-plus-compatibility slice.

## Git and merge

- Branch: `change/094-documentation-authority-refresh`
- Worktree: `.work/worktrees/094-documentation-authority-refresh`
- Candidate implementation commit: pending.
- Pull request: pending.
- Merge: pending.
- Cleanup: pending until the branch is merged into clean primary `main`.

## Residual items

- `SPEC.md` was reviewed as current-product authority but intentionally excluded because active parallel change `093-change-intelligence-enrichment` exclusively owns it. No 094 edit is required to establish documentation routing because that routing is owned by `AGENTS.md`.
- Supporting/historical documents identified as stale by the operator audit were intentionally not rewritten; higher authorities now define the current rule and current operator behavior.
