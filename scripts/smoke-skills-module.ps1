[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$Python = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'
$StateRoot = 'C:\Projects\.kis-mcp'

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'SKILLS_SMOKE_PYTHON_NOT_FOUND: run scripts\bootstrap-python.ps1 first.'
}
if (-not (Test-Path -LiteralPath 'C:\Projects\.agents\skills' -PathType Container)) {
    throw 'SKILLS_SMOKE_ROOT_NOT_FOUND: C:\Projects\.agents\skills is required.'
}

$previousPythonPath = $env:PYTHONPATH
$previousTemp = $env:TEMP
$previousTmp = $env:TMP
$previousCache = $env:PYTHONPYCACHEPREFIX
try {
    $env:PYTHONPATH = Join-Path $RepositoryRoot 'src'
    $env:TEMP = Join-Path $StateRoot 'temp'
    $env:TMP = Join-Path $StateRoot 'temp'
    $env:PYTHONPYCACHEPREFIX = Join-Path $StateRoot 'python-cache'
    $env:NO_UPDATE_NOTIFIER = '1'
    & $Python -B (Join-Path $PSScriptRoot 'smoke-skills-module.py')
    if ($LASTEXITCODE -ne 0) {
        throw "SKILLS_SMOKE_FAILED: smoke script exited with $LASTEXITCODE."
    }
}
finally {
    $env:PYTHONPATH = $previousPythonPath
    $env:TEMP = $previousTemp
    $env:TMP = $previousTmp
    $env:PYTHONPYCACHEPREFIX = $previousCache
}
