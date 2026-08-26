# Skills Degraded Readiness Implementation Plan

**Goal:** Make Skills catalogue initialization failure machine-observable without preventing ordinary Work startup.

**Architecture:** Keep the existing unavailable Skills service and two-value registration contract. Derive an immutable `SkillsRuntimeStatus` from the registered service, retain that status inside the composed gateway instance, project it additively through `kis_health.implementation_status`, and synthesize one degraded `skills.catalogue` capability contribution when the catalogue is unavailable.

**Tech Stack:** Python 3.13, FastMCP 4, pytest, Ruff, KIS change governance.

## Tasks

1. Preserve malformed-catalogue fail-open behavior and exact corrective Skills errors.
2. Add the immutable ready/degraded Skills runtime-status value.
3. Add degraded `skills.catalogue` capability readiness without private tool-layer coupling.
4. Project instance-local Skills state through `kis_health` while preserving global `ready` semantics.
5. Preserve the existing two-value `register_platform_skills` contract.
6. Cover ready/degraded status, registration compatibility, capability readiness, health projection, and dependency direction.
7. Run affected tests, Ruff, change-scope validation, architecture/API reviews, then publish for exact-head canonical verification.
