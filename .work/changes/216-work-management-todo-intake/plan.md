# Work Management Todo Intake Implementation Plan

**Goal:** Make provider `Todo` intake compatible with the governed Work Management lifecycle for #415.

**Architecture:** Add configured intake aliases to the command-plane settings contract. Resolve only configured undeclared ingress states through those aliases before normal lifecycle validation; keep declared states and unknown states unchanged/fail-closed.

**Tech Stack:** Python, JSON Schema, pytest, PowerShell governance wrapper.

## Constraints

- Work Management remains the only supported Ready/claim/Active transition authority.
- Do not broaden lifecycle transitions merely to accommodate provider defaults.
- Do not rewrite existing legitimate lifecycle states.
- Preserve existing readiness metadata requirements and claim semantics.

## Tasks

1. Add regression coverage for GitHub Project `Todo` progressing through `inbox` semantics to `Ready`.
2. Add a strict `intake_aliases` settings contract and configure `todo -> inbox`.
3. Resolve configured intake aliases before normal lifecycle parsing.
4. Update `SPEC.md` current-behavior truth.
5. Run focused tests, scope check, required review, exact-head CI, merge, Work reconciliation, and cleanup.
