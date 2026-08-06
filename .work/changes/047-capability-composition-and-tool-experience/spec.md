# Specification: Capability Composition and Tool Experience

## Outcome

Implement the approved 047 architecture from current `main`: normalized domain capability contributions, instance-scoped readiness, deterministic eligibility and explainable scoring, readiness-aware progressive exposure, first-class workflow descriptors, capability-bearing Skills metadata, and a thin `server.py`.

## Updated dependency decision

Change 040 is deferred by operator instruction and its worktree remains untouched. This change introduces only the generic `tools/platform.py` composition entry point required by 047. It does not import, install, register, or modify Context7 or Serena. A resumed 040 must integrate its adapters through the resulting Tools platform contract.

## Required behavior

1. Providers, Tools, Discover, Skills, and Workflows expose normalized `CapabilityContribution` records through domain `platform.py` entry points.
2. Registration, readiness, recommendation, and exposure remain separate concepts.
3. Eligibility hard-filters disabled, unregistered, unavailable, credential-blocked, dependency-blocked, and effect-incompatible operations before scoring.
4. Intrinsic quality and contextual suitability are deterministic, settings-driven, and explainable.
5. Scoring never authorizes Work, overrides HR-001/002/003, bypasses approval, or suppresses an explicitly requested valid operation.
6. The direct profile is curated; long-tail operations remain discoverable through `search_capabilities`, `describe_capability`, and `recommend_workflow`.
7. Unavailable provider operations remain visible in status/catalogue evidence but are not normally exposed or recommended.
8. Workflows describe complete user tasks and required capability steps without importing adapter internals.
9. Skills must have non-empty category and capability metadata before contribution.
10. Runtime composition state is explicit and instance-scoped; no global latest-composition state remains.
11. `server.py` delegates gateway construction to `compose_gateway(...)` and retains startup only.
12. Existing three-rule enforcement, middleware ordering, provider failure containment, current public behavior, and startup semantics remain intact unless intentionally replaced by the approved progressive exposure contract.

## Non-goals

- No policy changes or fourth hard rule.
- No Context7 or Serena implementation.
- No network access, package installation, credential changes, deployment, or destructive migration.
- No unrestricted generic execute-action tool.
- No claim that target-state Govern is implemented.

## Verification

Use TDD for each behavior slice, focused tests after each task, architecture checks, change scope validation, documentation drift checks, `git diff --check`, and final `pwsh -NoProfile -File scripts/verify.ps1`.
