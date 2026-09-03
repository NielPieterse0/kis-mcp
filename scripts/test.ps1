[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArguments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$StateRoot = 'C:\Projects\.kis-mcp'
$Python = Join-Path $StateRoot 'python-env\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'KIS_MCP_PYTHON_MISSING: run scripts\bootstrap-python.ps1 first.'
}

$PreviousPythonPath = [Environment]::GetEnvironmentVariable('PYTHONPATH', 'Process')
$PreviousNoUserSite = [Environment]::GetEnvironmentVariable('PYTHONNOUSERSITE', 'Process')

try {
    [Environment]::SetEnvironmentVariable('PYTHONPATH', (Join-Path $RepositoryRoot 'src'), 'Process')
    [Environment]::SetEnvironmentVariable('PYTHONNOUSERSITE', '1', 'Process')
    Push-Location $RepositoryRoot
    try {
        & $Python -m pytest @PytestArguments
        exit $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}
finally {
    [Environment]::SetEnvironmentVariable('PYTHONPATH', $PreviousPythonPath, 'Process')
    [Environment]::SetEnvironmentVariable('PYTHONNOUSERSITE', $PreviousNoUserSite, 'Process')
}
