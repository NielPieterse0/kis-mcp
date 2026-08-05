$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$verificationScript = Join-Path $repositoryRoot "scripts\verify.ps1"

& pwsh -NoProfile -File $verificationScript
exit $LASTEXITCODE
