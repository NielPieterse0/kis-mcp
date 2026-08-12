# Closeout: NIM Sub-agent Models

## Implemented scope

- Added a separate allowlisted NVIDIA benchmark catalog; production `nano`, `super`, and `ultra` profiles remain unchanged.
- Added a portable bounded benchmark request path through the existing approved NVIDIA external connector.
- Added fixed correctness/security capability scoring, 1-3 run repetition, and a 30-second suitability latency gate.
- Kept the benchmark out of the direct tool profile; capability discovery classifies it as eligible `external` + `read_only`.
- Pinned the NVIDIA base URL to `https://integrate.api.nvidia.com/v1` and kept credentials process-scoped/redacted.

## Validation evidence

- Focused implementation suite: passing after final hardening.
- Full repository verifier: one complete pass with pytest exit 0 plus configuration, interpreter, dependencies, syntax, line endings, change-governance, and three-rule checks passing.
- Final frozen-tree repository verifier: required before commit and merge.
- Diff scope check: passing; only 095-owned paths changed.

## Review

- Successful NVIDIA Nano code-quality review identified an external-boundary concern plus disabled-state test coverage.
- Resolution: external-boundary findings were reconciled against the authoritative approved-connector architecture; benchmark is explicitly external, not Work networking. Base URL pinning and disabled-state coverage were added as defense in depth.
- Two later Nano review attempts failed before producing findings (`NvidiaNimError`); they are runtime failures, not review approvals or findings.
- Codex review invocation exceeded the tool wait before returning a verdict; no Codex verdict is claimed.

## Git and merge

- Branch: `change/095-nim-subagent-models`
- Worktree: `.work/worktrees/095-nim-subagent-models`
- Base: `3eaf50d15282614a90a825e9878254a1e713bb31`
- Commit: recorded by final commit step.
- Pull request or merge: recorded by governed exact-head closeout.
- Cleanup: only after confirmed merge; unrelated 093 worktree remains untouched.

## Residual items

- Live model benchmarking occurs only after this benchmark seam is commissioned in a runtime that can securely resolve the existing NVIDIA secret.
- Candidate promotion, if any, is a separate bounded change driven only by live benchmark evidence; 095 itself does not promote experimental models.
