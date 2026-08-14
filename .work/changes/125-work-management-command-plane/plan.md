# Work Management Command Plane Implementation Plan

**Goal:** Deliver the approved command-plane architecture in tested vertical slices while using issue #177 / Project #1 as the live commissioning case.

**Architecture:** GitHub Project is the operational command plane; repository/Git/Actions remain evidence authorities; KIS performs directional reconciliation through provider-neutral Work Management services. Authority, state, ranking, classification, and safeguard definitions are checked-in configuration.

**Tech stack:** Python 3.12, FastMCP, existing Work Management reconciliation backend, official GitHub MCP provider, pytest, JSON settings/contracts.

## Global constraints

- Stay inside `scope.json`; do not edit paths claimed by concurrent slices.
- Add/adjust focused tests before behavior changes.
- Preserve historical WorkRecord compatibility while moving new operational behavior to Work State + Delivery Stage.
- Do not add unrestricted network/provider implementations.
- Run focused tests after each phase; canonical full verification remains exact-head CI.

## Phase 1 — Authority and classification configuration

- Define command-plane settings/schema: authority map, Work State transitions, Ready requirements, deterministic priority/effort/age ranking, and claim rules.
- Externalize change complexity/risk/review/verification controls into one checked-in governance settings file shared by change governance and execution.
- Extend domain vocabulary with Ready, Effort, Delivery Stage, and claim metadata.
- Focused tests: settings/contracts, change-controls, change-governance.

## Phase 2 — Intake and deterministic work selection

- Add the standard Work Item issue form with bounded title/body guidance.
- Replace legacy next-work selection with settings-driven Ready/unclaimed ranking while keeping explanatory exclusions.
- Add pure claim/release/transition decisions and tests before provider mutation wiring.
- Focused tests: intake, selection, lifecycle, command-plane domain tests.

## Phase 3 — Project command operations

- Build ergonomic service operations that read live Project state and construct reconciliation decisions internally.
- Expose next, claim, release, hold, defer, transition, and complete task-level tools through the existing Project Management subserver.
- Require preview/idempotency for mutations and current observed evidence; never use last-write-wins.
- Focused tests: service, tools, reconciliation conflict paths.
