param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArguments
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$StateRoot = 'C:\Projects\.kis-mcp'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $StateRoot 'python-env'
$env:UV_CACHE_DIR = Join-Path $StateRoot 'uv-cache'
$env:PYTHONPYCACHEPREFIX = Join-Path $StateRoot 'python-cache'
$env:UV_OFFLINE = '1'
$env:PYTHONPATH = Join-Path $RepositoryRoot 'src'
$env:TEMP = Join-Path $StateRoot 'temp'
$env:TMP = Join-Path $StateRoot 'temp'

Push-Location $RepositoryRoot
try {
    & uv run --offline --no-sync python scripts\project_workflow.py @CommandArguments
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
