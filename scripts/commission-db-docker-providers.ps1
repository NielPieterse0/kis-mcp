$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'windows-credential.ps1')
. (Join-Path $PSScriptRoot 'secret-vault.ps1')
. (Join-Path $PSScriptRoot 'provider-secrets.ps1')

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "KIS_MCP_PYTHON_MISSING: $Python"
}

$Code = @'
import asyncio, json, os
from pathlib import Path
from kis_mcp.projects import load_project_registry_settings
from kis_mcp.providers.commissioning import commissioning_evidence_root, write_commissioning_evidence
from kis_mcp.providers.dbhub.provider import dbhub_commissioning_identity, dbhub_provider_descriptor
from kis_mcp.providers.dbhub.settings import load_dbhub_settings
from kis_mcp.providers.dockerhub.provider import dockerhub_commissioning_identity, dockerhub_provider_descriptor
from kis_mcp.providers.dockerhub.settings import load_dockerhub_settings

root = Path.cwd()
environment = dict(os.environ)
evidence_root = commissioning_evidence_root(root)
rows = []
for name, factory in (
    ("dbhub", dbhub_provider_descriptor),
    ("dockerhub-mcp", dockerhub_provider_descriptor),
):
    descriptor = factory(repository_root=root, environment=environment)
    readiness = descriptor.readiness_probe()
    row = {"provider_id": name, "readiness": readiness.to_json_dict(), "live_verified": False, "tools": []}
    if readiness.state.value == "ready":
        try:
            server = descriptor.builder()
            tools = asyncio.run(server.list_tools())
            row["tools"] = sorted(tool.name for tool in tools)
            if name == "dbhub":
                identity = dbhub_commissioning_identity(
                    load_dbhub_settings(root),
                    load_project_registry_settings(root / "settings" / "projects.settings.json"),
                )
            else:
                identity = dockerhub_commissioning_identity(load_dockerhub_settings(root))
            evidence_path = write_commissioning_evidence(
                evidence_root,
                name,
                identity,
                row["tools"],
            )
            row["commissioning_evidence"] = str(evidence_path)
            row["live_verified"] = True
        except Exception as exc:
            row["live_error_type"] = type(exc).__name__
    rows.append(row)
print(json.dumps({"providers": rows}, sort_keys=True))
raise SystemExit(0 if all(row["live_verified"] for row in rows) else 2)
'@

$ProviderSecrets = Resolve-KisMcpProviderSecretEnvironment -RepositoryRoot $RepositoryRoot
$Info = [System.Diagnostics.ProcessStartInfo]::new()
$Info.FileName = $Python
$Info.WorkingDirectory = $RepositoryRoot
$Info.UseShellExecute = $false
$Info.RedirectStandardOutput = $true
$Info.RedirectStandardError = $true
$Info.ArgumentList.Add('-c')
$Info.ArgumentList.Add($Code)
$Info.Environment['PYTHONPATH'] = Join-Path $RepositoryRoot 'src'
foreach ($Name in @($ProviderSecrets.Keys)) {
    $Info.Environment[$Name] = [string]$ProviderSecrets[$Name]
}

$Process = [System.Diagnostics.Process]::new()
$Process.StartInfo = $Info
try {
    if (-not $Process.Start()) { throw 'KIS_MCP_PROVIDER_COMMISSION_START_FAILED' }
    foreach ($Name in @($ProviderSecrets.Keys)) { $Info.Environment.Remove($Name) }
    Clear-KisMcpProviderSecretEnvironment -Environment $ProviderSecrets
    $Output = $Process.StandardOutput.ReadToEnd()
    $ErrorOutput = $Process.StandardError.ReadToEnd()
    $Process.WaitForExit()
    if ($Output) { Write-Output $Output.Trim() }
    if ($ErrorOutput) { [Console]::Error.WriteLine($ErrorOutput.Trim()) }
    exit $Process.ExitCode
}
finally {
    Clear-KisMcpProviderSecretEnvironment -Environment $ProviderSecrets
    $Process.Dispose()
}
