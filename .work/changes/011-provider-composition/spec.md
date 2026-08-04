# Specification: 011 Provider Composition

## Outcome

Provide one explicit provider-neutral composition API that registers Desktop Commander, GitHub, and Supabase without building, starting, authenticating, or contacting any provider.

## Requirements

- Add a Desktop Commander `ProviderDescriptor` adapter around existing Work configuration, builder, and offline readiness.
- Preserve Desktop Commander ownership under Work and HR-001 through HR-003.
- Register Desktop Commander, GitHub, and Supabase in deterministic order through the shared `ProviderRegistry`.
- Expose a `ProviderService` factory for catalogue and aggregate readiness inspection.
- Keep registration explicit; imports must not register, build, start, authenticate, or use network access.
- Contain Desktop Commander readiness failures as redacted provider-neutral evidence.
- Do not edit `server.py` while active Discover owns a shared claim on that composition root.

## Acceptance

- Catalogue contains exactly the three approved providers.
- Catalogue and registration invoke no builders or readiness probes.
- Health invokes readiness probes only and builds no provider.
- Desktop Commander readiness reports ready/unavailable without exposing raw exception messages.
- GitHub and Supabase remain isolated adapters.
- Full repository verification, governed scope check, and whitespace validation pass.
