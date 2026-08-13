# Two-Axis Change Governance Implementation Plan

> **For agentic workers:** Execute task-by-task in this governed worktree. Use focused verification during development; reserve the canonical full verifier for the exact PR head.

**Goal:** Separate workload complexity from additive risk controls and expose both consistently through change governance and Work Management.

**Architecture:** Introduce schema-v4 change records as the authority for complexity and risk triggers while retaining schema-v1–v3 read compatibility. Work Management receives optional normalized classification plus two projected Project fields. Change-execution integration waits for change 116 to release its exclusive claim.

**Tech Stack:** Python 3, pytest, PowerShell, FastMCP, GitHub Projects provider, JSON configuration.

## Global constraints

- Stay inside the declared scope and expand it before touching a new path.
- Do not modify the two operator-owned classification skills.
- Preserve exactly HR-001, HR-002, and HR-003.
- Keep Work Management projection-only.
- Preserve schema-v1–v3 stored-record compatibility.
- Keep SPEC-117 open for operator closeout.
