# Context7 and Serena provider commissioning

## Boundary

Context7 and Serena are Provider-runtime integrations, not new project identity or memory systems.

- Context7 is an independent approved external documentation connector.
- Serena is an optional local semantic-code provider for Discover.
- Discover persists only normalized KIS Code Atlas, Symbol Atlas, and Relationship Graph evidence.
- Serena-managed `.serena/memories` files are provider state and are never KIS project memory.
- Deterministic Python AST and static JavaScript/TypeScript analysis remains available when Serena is absent, disabled, unhealthy, partial, or incompatible.

## Pinned identities

Context7:

- package: `@upstash/context7-mcp@3.2.5`
- source revision: `b250c2515694eee4b6df4db82fa056df9ed3e306`
- package integrity: recorded exactly in `settings/providers/context7.provider.json`
- public tools: `resolve-library-id`, `query-docs`

Serena:

- package: `serena-agent==1.6.1`
- source revision: `bcac0969fb8685783ea6d0f2642468fcc47e6395`
- wheel SHA-256: `04ddd985bd3feb25598ab8732bf3a998f961d5b46dce271b816126c0a68a91e1`

## Serena launch and exposed surface

The promoted Windows console launcher is not used. A Python venv console script embeds its creation-time interpreter path and the 040 promoted `serena.exe` stopped working after its staged venv moved into the final install root.

The canonical runtime launches the relocated venv interpreter directly:

```text
C:\Projects\.kis-mcp\serena\venv\Scripts\python.exe
-c "from serena.cli import top_level; top_level()"
start-mcp-server ...
```

The Provider runtime supplies contained HOME/AppData/TEMP roots and forces `UV_OFFLINE=1` plus `SERENA_USAGE_REPORTING=false`. This is required because the pinned Serena Python language-server path invokes `uvx` for the pinned Pyright distribution. If the required local asset is unavailable, Serena must degrade instead of acquiring it from the network.

Only these Serena operations are mounted publicly:

- `get_symbols_overview`
- `find_symbol`
- `find_referencing_symbols`

`activate_project` is an internal lifecycle operation. Upstream edit, shell, dashboard, and memory mutation tools are not exposed through the Serena provider mount.

Discover and the mounted provider share one `SerenaRuntimeAdapter`/upstream client lifecycle. Provider-specific result schemas are normalized before entering Discover persistence or impact/context contracts.

## HR3-07 Serena memory safety

Pinned Serena 1.6.1 source establishes the complete `delete_memory` artifact set: one resolved Markdown memory file. `list_memories` derives its catalogue by scanning memory files; the delete method does not update a persistent catalogue or index sidecar.

KIS therefore intercepts the proven delete target as follows:

1. validate the exact pinned Serena version and bounded memory name;
2. resolve the single complete affected artifact;
3. reject traversal, alias, wildcard, or outside-boundary paths;
4. quarantine the complete existing artifact set through `QuarantineService`;
5. do not forward upstream `delete_memory` after successful quarantine;
6. restore only through ordinary recoverable quarantine restoration;
7. restart/reinspect Serena and verify the derived catalogue and content.

If a later Serena version changes this artifact contract, the safety proof no longer applies and must be re-established before the operation can be considered safely intercepted.

## Commissioning

Run:

```powershell
$env:UV_PROJECT_ENVIRONMENT='C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR='C:\Projects\.kis-mcp\uv-cache'
uv run --offline --no-sync python scripts\run-provider-live-smoke.py --output .work\changes\<change-id>\provider-live-smoke.json
```
The smoke is intentionally bounded:

- Context7 proves local MCP startup and exact tool discovery; it does not bypass HR-002 to force an external documentation query.
- Serena proves exact upstream tool discovery, project activation, semantic overview, offline language-server startup, quarantine-only HR3-07 handling, restoration, restart, and post-restoration catalogue/content consistency.
- Temporary commissioning projects remain beneath `C:\Projects\.kis-mcp\commissioning` as generated state.
- No credentials or repository secrets are persisted in the commissioning record.

For change 084, the retained evidence is `.work/changes/084-discover-persistent-memory-closeout/provider-live-smoke.json`.