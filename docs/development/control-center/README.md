# KIS Control Center

The KIS Control Center is a separate, read-only MCP App for local operational visibility. It does not modify or replace Desktop Commander and it is not part of the three-rule Work enforcement path.

## Current surface

The standalone server exposes:

- `open_kis_control_center` — returns a current structured local snapshot and links the host to the Control Center UI;
- `ui://kis-mcp/control-center.html` — a self-contained MCP App resource using `text/html;profile=mcp-app`.

The snapshot includes:

- runtime identity and Desktop Commander installation evidence;
- configured project path and fixed-template local Git status;
- the exact HR-001, HR-002, and HR-003 policy declaration;
- provider configuration entries labelled `runtime_check_required`;
- bounded quarantine counts;
- the configured verification command labelled `not_recorded` until current evidence is run;
- structural diagnostics for unavailable or invalid local inputs.

Configuration never proves provider authentication, commissioning, connectivity, or current verification. Use `kis_provider_status` and the normal supervised Work surface for those actions and evidence.

## Run

From `C:\Projects\kis-mcp`:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m kis_mcp.control_center
```

The module reads `settings\control-center.settings.json`. Set `KIS_CONTROL_CENTER_SETTINGS` to an alternate absolute JSON path when a supervised local profile is required.

## UI boundary

The HTML resource:

- contains no external scripts, styles, images, fonts, frames, or network requests;
- renders runtime-derived text only after HTML escaping;
- uses host-provided MCP App theme variables with safe local fallbacks;
- performs no mutation, process launch, provider action, verification run, or quarantine restore.

Hosts that do not render MCP Apps still receive the same snapshot as structured tool content.

## Integration boundary

This slice intentionally does not modify `src/kis_mcp/server.py`, which is owned by another active change. Mounting the Control Center provider into the primary gateway is a later additive integration step. The standalone package and contract are complete independently of that mount.

## Verification

Focused tests:

```powershell
pwsh -NoProfile -File .work\changes\036-kis-control-center\run-focused-tests.ps1 tests\control_center -q
```

Repository verification:

```powershell
pwsh -NoProfile -File scripts\verify.ps1
```
