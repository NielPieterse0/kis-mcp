[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "KIS_MCP_PYTHON_MISSING: $Python"
}

$PreviousPythonPath = [Environment]::GetEnvironmentVariable('PYTHONPATH', 'Process')
$PreviousPluginAutoload = [Environment]::GetEnvironmentVariable(
    'PYTEST_DISABLE_PLUGIN_AUTOLOAD',
    'Process'
)
try {
    [Environment]::SetEnvironmentVariable(
        'PYTHONPATH',
        (Join-Path $RepositoryRoot 'src'),
        'Process'
    )
    [Environment]::SetEnvironmentVariable(
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD',
        '1',
        'Process'
    )
    Push-Location $RepositoryRoot
    try {
        & $Python -m pytest @PytestArgs
        exit $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}
finally {
    [Environment]::SetEnvironmentVariable('PYTHONPATH', $PreviousPythonPath, 'Process')
    [Environment]::SetEnvironmentVariable(
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD',
        $PreviousPluginAutoload,
        'Process'
    )
}
