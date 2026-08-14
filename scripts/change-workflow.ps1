param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArguments
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'configure-repository.ps1')
$StateRoot = 'C:\Projects\.kis-mcp'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $StateRoot 'python-env'
$env:UV_CACHE_DIR = Join-Path $StateRoot 'uv-cache'
$env:PYTHONPYCACHEPREFIX = Join-Path $StateRoot 'python-cache'
$env:TEMP = Join-Path $StateRoot 'temp'
$env:TMP = Join-Path $StateRoot 'temp'
$env:UV_OFFLINE = '1'

Push-Location $RepositoryRoot
try {
    if ($CommandArguments.Count -ge 2 -and $CommandArguments[0] -eq 'cleanup') {
        & uv run --offline --no-sync python scripts\git-workflow.py --repository $RepositoryRoot prepare-cleanup --change-id $CommandArguments[1]
        if ($LASTEXITCODE -ne 0) {
            throw "Change cleanup preparation failed with exit code $LASTEXITCODE"
        }
    }

    & uv run --offline --no-sync python scripts\change-governance.py --repository $RepositoryRoot @CommandArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Change governance failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
