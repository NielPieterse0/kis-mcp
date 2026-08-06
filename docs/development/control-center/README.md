# KIS Control Center

The KIS Control Center is a separate KIS-owned, read-only MCP App for local operational visibility. It does not modify, wrap, vendor, fork, or replace Desktop Commander, and it is not a second Work enforcement boundary.

## Normal use

The normal kis-mcp gateway mounts Control Center through the provider runtime under namespace `controlcenter`.

After the kis-mcp connector is restarted or refreshed, the host exposes:

- `controlcenter_open_kis_control_center` — opens the MCP App and returns the current structured snapshot as fallback content;
- `ui://controlcenter/kis-mcp/control-center.html` — the mounted self-contained MCP App resource using `text/html;profile=mcp-app`.

No second server process is required. The standalone command is optional diagnostic mode only; it starts a stdio MCP server and does not open a browser or application window:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m kis_mcp.control_center
```

In standalone mode the base tool/resource identities remain `open_kis_control_center` and `ui://kis-mcp/control-center.html`.

## Dashboard evidence

The dashboard presents a fresh bounded local snapshot containing:

- runtime identity and Desktop Commander installation evidence;
- configured project path and fixed-template local Git state;
- bounded local Discover project, language, framework, module, finding, confidence, and truncation evidence;
- the exact HR-001, HR-002, and HR-003 policy declarations;
- bounded pending operator decisions parsed read-only from the existing hard-block approval register;
- configured providers separately from current registration, build, mount, readiness, action, and commissioning evidence;
- bounded recent tool-call and policy-decision records containing tool names and argument key names only;
- active managed process and search lifecycle for the current gateway process;
- bounded quarantine counts and recent recoverable records;
- available supervised action names for Discover, provider status, quarantine listing/restoration, and verification;
- explicit verification state and structural diagnostics.

Configuration never proves provider authentication, connectivity, commissioning, or live verification. Unknown and degraded states remain explicit. Discover and provider-evidence failures degrade only their respective dashboard sections.

## Read-only and privacy boundary

The Control Center:

- contains no external scripts, styles, images, fonts, frames, or network requests;
- escapes all runtime-derived text before rendering;
- uses host-provided light/dark theme variables and host typography with local fallbacks;
- retains no raw tool argument values or result bodies in recent-call observability;
- performs no file mutation, quarantine restore, process termination, verification execution, provider authentication, or settings change;
- displays operational action names but requires execution through the supervised kis-mcp tool surface.

Desktop Commander remains responsible for file previews, editing, directory browsing, document rendering, and its own configuration widgets.

## Configuration

The Control Center reads `settings\control-center.settings.json`, validated by `contracts\control-center\settings.schema.json`.

Configuration controls:

- local evidence source paths;
- whether bounded Discover collection is enabled;
- provider, approval, recent-call, policy-decision, process, search, Discover-finding, and quarantine limits;
- Git timeout and JSON input byte limits;
- the verification command shown as guidance.

Set `KIS_CONTROL_CENTER_SETTINGS` to an alternate absolute JSON file only for a supervised local profile.

## Verification

Focused Control Center and integration tests:

```powershell
pwsh -NoProfile -File .work\changes\036-kis-control-center\run-focused-tests.ps1 tests\control_center tests\providers\test_control_center_provider.py tests\providers\test_platform_composition.py tests\providers\test_runtime_composition.py -q
```

Repository verification:

```powershell
pwsh -NoProfile -File scripts\verify.ps1
```
