# Change 171 — UI default off

## Outcome

Keep the KIS MCP runtime active while the Control Center MCP App/UI provider is disabled in the default checked-in runtime composition.

## Acceptance

- `control-center` remains registered but is disabled by default in platform runtime settings.
- Ordinary MCP backend providers and Work/Discover/Skills behavior remain unchanged.
- Operators can re-enable the UI explicitly by setting the existing `control-center` provider entry to `enabled: true` and restarting the selected runtime instance.
- Focused runtime-composition tests prove the checked-in default is UI-off.
- Current product specification states the default-off behavior without changing HR-001/HR-002/HR-003 semantics.
