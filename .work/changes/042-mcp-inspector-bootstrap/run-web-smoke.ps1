$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$LauncherScript = Join-Path $RepositoryRoot 'scripts\start-mcp-inspector.ps1'
$PowerShell = (Get-Command 'pwsh.exe' -CommandType Application | Select-Object -First 1).Source
$Url = 'http://127.0.0.1:6275/'

$StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
$StartInfo.FileName = $PowerShell
$StartInfo.UseShellExecute = $false
$StartInfo.CreateNoWindow = $true
$StartInfo.RedirectStandardOutput = $true
$StartInfo.RedirectStandardError = $true
$StartInfo.ArgumentList.Add('-NoProfile')
$StartInfo.ArgumentList.Add('-File')
$StartInfo.ArgumentList.Add($LauncherScript)
$StartInfo.ArgumentList.Add('-Instance')
$StartInfo.ArgumentList.Add('development')
$StartInfo.ArgumentList.Add('-NoBrowser')
$StartInfo.ArgumentList.Add('-RepositoryRoot')
$StartInfo.ArgumentList.Add($RepositoryRoot)

$Process = [System.Diagnostics.Process]::new()
$Process.StartInfo = $StartInfo
$Started = $Process.Start()
if (-not $Started) {
    throw 'MCP_INSPECTOR_WEB_SMOKE_START_FAILED'
}

$StatusCode = $null
try {
    for ($Attempt = 0; $Attempt -lt 80; $Attempt++) {
        if ($Process.HasExited) {
            break
        }
        try {
            $Response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 1
            $StatusCode = [int]$Response.StatusCode
            if ($StatusCode -eq 200) {
                break
            }
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    }

    if ($StatusCode -ne 200) {
        throw "MCP_INSPECTOR_WEB_SMOKE_FAILED: no HTTP 200 from $Url"
    }
}
finally {
    if (-not $Process.HasExited) {
        $Process.Kill($true)
    }
    $Process.WaitForExit()
}

$StandardOutput = $Process.StandardOutput.ReadToEnd()
$StandardError = $Process.StandardError.ReadToEnd()
$RedactedOutput = [regex]::Replace(
    $StandardOutput,
    '(MCP_INSPECTOR_API_TOKEN=|Auth token:\s*)[0-9a-f]+',
    '$1[redacted]',
    [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
)
[ordered]@{
    ok = $true
    url = $Url
    status_code = $StatusCode
    process_terminated_after_smoke = $true
    launcher_output = $RedactedOutput.Trim()
    launcher_error = $StandardError.Trim()
} | ConvertTo-Json -Depth 4
