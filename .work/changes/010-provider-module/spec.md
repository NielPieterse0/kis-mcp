# 010 Provider Module Specification

## Outcome

Create the common `kis_mcp.providers` module boundary that owns provider-neutral contracts, deterministic registration, progressive catalogue projection, aggregate readiness, and a thin service facade. Capture the approved platform architecture and Provider module architecture in a canonical product specification.

## Approved architecture

```text
ChatGPT
   |
   v
kis-mcp FastMCP platform
├── shared tool catalogue / routing
├── provider registry
├── health and readiness
│
├── Work Module
│     └── three-rule middleware
│           ├── HR-001: no writes outside C:\Projects
│           ├── HR-002: no external network through Work
│           └── HR-003: no permanent deletion
│                 |
│                 v
│        Desktop Commander MCP
│        ├── filesystem
│        ├── editing
│        ├── search
│        ├── terminal
│        ├── process
│        └── document operations
│
├── Providers Module
│     ├── GitHub MCP provider
│     ├── Supabase MCP provider
│     └── future provider adapters
├── Govern Module
└── Discover Module
```

## Boundary

The Provider module owns provider-neutral identity, capability, lifecycle, readiness, catalogue, and registration contracts. Each connector owns its transport, settings, authentication indirection, provider-specific validation, and server construction beneath a dedicated adapter package.

The Provider module does not own Work enforcement, provider-specific credentials, connector network policy, Discover evidence normalization, Govern admission decisions, or provider installation.

## Components

- `contracts.py`: immutable provider-neutral enums and records.
- `registry.py`: deterministic in-memory registration and lookup with duplicate rejection.
- `catalogue.py`: immutable sorted catalogue projection and filtering.
- `health.py`: aggregate readiness calculation without invoking connector networks.
- `service.py`: thin composition facade over registry, catalogue, and health.
- `__init__.py`: explicit public surface only.
- `contracts/providers/module/provider-module.schema.json`: versioned JSON contract snapshot.

## Connector relationship

Changes `008-github-mcp-provider` and `009-supabase-mcp-provider` remain owners of their connector-specific directories. This slice must not edit those active paths. Their adapters already reside beneath `src/kis_mcp/providers/github` and `src/kis_mcp/providers/supabase`; after dependency integration they must register descriptors conforming to this module contract. The existing temporary root-level `provider_registry.py` from change 008 is not modified here and should become a compatibility shim or be retired in a coordinated follow-up after 008 is integrated.

## Acceptance criteria

1. Provider descriptors validate stable identity, kind, boundary, source, revision, capabilities, and builder/readiness callbacks.
2. Duplicate provider IDs fail deterministically.
3. Registry listing and catalogue output are stable and sorted.
4. Capability filtering does not load or start providers.
5. Aggregate readiness reports ready, degraded, disabled, and unavailable states without network access.
6. The service facade contains no provider-specific branches.
7. Public imports are explicit and versioned.
8. JSON schema matches the public record shape.
9. Tests prove isolation and deterministic behavior with synthetic providers.
10. Documentation contains the approved platform diagram, Provider module structure, dependency direction, extension contract, migration path for GitHub and Supabase, and non-goals.
11. No file in the active GitHub, Supabase, Discover, or Work slices is modified.
12. No new hard rule, tool restriction, credential handling, network access, dependency, or runtime provider activation is introduced.

## Modularity assessment decision

The subject units are the common Provider core, GitHub adapter, Supabase adapter, Discover module, and Work module. Direct inspection supports a domain boundary: shared provider lifecycle contracts belong together, while transport-specific behavior remains in isolated adapters. Change history and agent read/edit ratios are unmeasured because the relevant branches are active and partially untracked, so MAS is `n/a`. The reversible recommendation is to establish the common contract now, preserve adapter packages, and defer connector import migration until dependencies 008 and 009 are integrated.

## Verification

- Focused tests: `pytest tests/providers/test_provider_module.py -q` through the repository interpreter.
- Contract JSON validation.
- Change scope check; the known duplicate historical-claim defect may block repository-wide governance validation and must be recorded without weakening scope discipline.
- Full repository verification through `scripts/verify.ps1`.
- Git diff and whitespace checks.

## Recovery

The branch is isolated at `.work/worktrees/010-provider-module`. No existing runtime file is replaced. Recovery is branch abandonment or recoverable quarantine of newly created files. The PR must remain unmerged pending review.
