# Defender Safe Agnix Implementation Plan

**Goal:** Close #530 by replacing the blocked Windows helper runtime with a provenance-verified WSL2 execution path while preserving agnix behavior and KIS authority.

**Architecture:** KIS owns generated agnix state under `C:\Projects\.kis-mcp\tools`. The supervised bootstrap downloads the exact `agent-sh/agnix` Linux x86_64 v0.45.0 release and checksum sidecar, verifies SHA-256, smoke-tests through WSL2 Ubuntu, then promotes recoverably. The validation service maps Windows project/tool paths to `/mnt/c/...` and calls only fixed agnix validation arguments through `wsl.exe`.

**Tech Stack:** PowerShell, Python, WSL2 Ubuntu, agnix 0.45.0.

## Constraints

- Preserve HR-001/HR-002/HR-003 and existing validation authority.
- No Defender/SAC weakening, exclusions, trusted-folder assumptions, or copied Windows PE remediation.
- No unrelated Node reinstall: evidence proves `agnix-binary.exe`, not Node, is blocked.

## Tasks

1. Add failing tests for KIS runtime ownership, upstream Linux asset provenance, WSL invocation, and explicit SAC error classification.
2. Implement settings, supervised installer, WSL path mapping, and deterministic launch-block error.
3. Run installer and real agnix workload; quarantine stale repo-local Windows runtime.
4. Capture fresh Code Integrity evidence and repository schema/malformed-config acceptance evidence.
5. Reconcile `SPEC.md`, setup runbook, bootstrap evidence, and change records.
6. Run focused tests and change-governance check, review, publish, exact-head CI, merge, live KIS proof, and closeout.
