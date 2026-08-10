# Closeout: NVIDIA NIM Model Profiles

## Implemented scope

- Replaced the single NVIDIA model record with strict `nano`, `super`, and `ultra` profiles; `super` is the default.
- Added exact per-profile model IDs, sampling/reasoning parameters, non-streaming request construction, and operator guidance.
- Added explicit `model` selection to `review_change_with_agent`, NVIDIA model provenance, invalid model/backend handling, and preserved no-model NVIDIA→Codex fallback.
- Added canonical NVIDIA vault reference `secret://provider/nvidia-nim/api-key`; `.env/` is ignored and the operator-supplied plaintext bootstrap was migrated into the encrypted vault then quarantined recoverably.
- Updated `start-chatgpt.ps1` so the selected server child receives process-scoped `NVIDIA_API_KEY`; tunnel credential handling remains on Windows Credential Manager and peer-instance lifecycle remains isolated.
- Updated current specification/operations guidance and preserved the separate follow-up boundary for Codex as an independent code-quality and safety/security reviewer.

## Validation evidence

- TDD: provider RED 8 intended failures → GREEN 8/8; reviewer RED 6 intended failures with 3 legacy passes → GREEN 9/9; startup RED 3 intended failures with 27 legacy passes → GREEN 30/30.
- Focused checks: provider + complete code-review + startup 55/55; broader providers + code-review + startup 287/287; corrected tunnel + startup 78/78.
- Repository verification: exact worktree `scripts/verify.ps1` passed; full pytest exit 0 with two expected skips, Python syntax 246 files, FastMCP 3.4.4, pytest 8.4.2, configuration/interpreter/dependencies/change-governance/line-endings all pass.
- Diff scope check: `scripts/change-workflow.ps1 check` passed after ownership was expanded only to the affected tunnel/startup test contract.
- Secret evidence: vault reference metadata verified with reference count 3; plaintext bootstrap quarantine ID `bd4412d2b9204e6e8e42c264f259feb5`.

## Review

- Static project review: 423 Python files analyzed; zero warning/error findings.
- Full-diff review: no policy changes, no unrelated provider changes, no credential values in repository configuration/output, tunnel remains Windows-Credential-backed, NVIDIA vault use is limited to selected server startup.
- Blocking findings: none after correcting two stale tunnel tests exposed by the first full verifier run.

## Git and merge

- Branch: `change/091-nvidia-nim-model-profiles`
- Worktree: `.work/worktrees/091-nvidia-nim-model-profiles`
- Design commit: `0f321f49e7c9d5610c0bff151696bbde6c0f5b95`
- Candidate implementation commit: `68d9e7f5f5d425d59a1aa15ba0fd7c92aff6c4c9`.
- Candidate `kis-dev` commissioning: PASS on development run `20260810T1220335123910Z`, repository root `C:\Projects\kis-mcp\.work\worktrees\091-nvidia-nim-model-profiles`. `kis_health.ready=true`; NVIDIA state `ready`; default profile `super`; public review schema exposes `model`; live reviews completed for Nano (`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`), Super (`nvidia/nemotron-3-super-120b-a12b`), and Ultra (`nvidia/nemotron-3-ultra-550b-a55b`). `kis-op` remained independently `ready=true` throughout.
- Final integrated-head `kis-dev` commissioning: pending after merge/publication/cleanup so the exact stable final head can be signed off without later repository drift.
- Final exact-head commissioning evidence will be retained beneath canonical generated state `C:\Projects\.kis-mcp\commissioning\091-nvidia-nim-model-profiles-final.json`; this record is written only after all repository mutations and cleanup are complete.
- Cleanup: pending.

## Residual items

- Codex CLI installation/authentication and independent code/safety-security review modes are intentionally deferred to the next separately commissioned slice.
