# Provider Composition

> **Historical implementation evidence.** This document records the provider-composition slice before runtime integration and NVIDIA NIM were added. It is preserved as development history and is not current operational guidance. Use [`../../PROVIDER-MODULE-PRODUCT-SPEC.md`](../../PROVIDER-MODULE-PRODUCT-SPEC.md), [`../../../SPEC.md`](../../../SPEC.md), and [`../../OPERATIONS.md`](../../OPERATIONS.md) for the current provider registry, runtime mounting, status, and onboarding model.

## Purpose

The platform composition layer registers the three approved provider boundaries through one shared `ProviderRegistry`:

```text
ProviderRegistry
├── desktop-commander  Work backend
├── github-mcp         approved external connector
└── supabase           approved external connector
```

Registration is explicit and inert. Building the registry or catalogue does not build, start, authenticate, probe, or contact a provider.

## Desktop Commander boundary

`kis_mcp.providers.desktop_commander` projects the existing Desktop Commander Work backend into the provider-neutral contracts. It does not move Desktop Commander into the external Providers plane and does not alter the Work middleware.

The descriptor declares:

- provider kind `local_backend`;
- boundary `work_backend`;
- pinned authoritative npm package and version;
- local filesystem, editing, search, process, and document capabilities;
- an explicit builder for the existing Work server;
- an offline readiness probe that redacts failure messages.

HR-001, HR-002, and HR-003 remain enforced only through the existing Work path.

## Platform factories

Use the explicit composition APIs:

```python
from kis_mcp.providers.platform import (
    build_platform_provider_registry,
    build_platform_provider_service,
)

registry = build_platform_provider_registry()
service = build_platform_provider_service()
```

`service.catalogue()` reads declared metadata only. `service.health()` executes readiness probes but never provider builders. `service.build(provider_id)` is the only operation that explicitly constructs the selected provider.

## Composition-root boundary

This slice intentionally does not edit `src/kis_mcp/server.py`. The active Discover change owns a coordinated shared claim on that composition root. Public MCP tools for provider catalogue or health can be added later through a separate integration slice after that claim closes.

## Verification

The tests prove:

- exact three-provider registration;
- deterministic catalogue order;
- no builds or probes during registry/catalogue construction;
- readiness probes without provider construction;
- Desktop Commander Work-boundary identity;
- redacted Desktop Commander readiness failures;
- unchanged exact three-rule repository verification.
