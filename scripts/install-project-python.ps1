$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'runtime-authority.ps1')
$Authority = Get-KisMcpRuntimeAuthority
$PythonExe = [System.IO.Path]::GetFullPath([string]$Authority.python.executable)
$PythonRoot = Split-Path -Parent $PythonExe
$Version = [string]$Authority.python.version
$StateRoot = 'C:\Projects\.kis-mcp'
$OperationId = 'install-project-python-' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$AcquisitionRoot = Join-Path $StateRoot "temp\$OperationId"
$Installer = Join-Path $AcquisitionRoot "python-$Version-amd64.exe"
$InstallerUrl = "https://www.python.org/ftp/python/$Version/python-$Version-amd64.exe"

if (-not (Test-KisMcpPathWithinBoundary -Path $PythonExe -Boundary ([string]$Authority.project_boundary))) {
    throw "KIS_PROJECT_PYTHON_BOUNDARY_VIOLATION: executable=$PythonExe"
}
if (Test-Path -LiteralPath $PythonExe -PathType Leaf) {
    $runtime = Resolve-KisMcpProjectPython -Authority $Authority
    Write-Host "Project Python already valid: $($runtime.executable)"
    exit 0
}

New-Item -ItemType Directory -Force -Path $AcquisitionRoot, $PythonRoot | Out-Null
Write-Host "Acquiring official CPython $Version for supervised installation..."
Invoke-WebRequest -Uri $InstallerUrl -OutFile $Installer
$signature = Get-AuthenticodeSignature -LiteralPath $Installer
$subject = if ($null -ne $signature.SignerCertificate) { [string]$signature.SignerCertificate.Subject } else { '' }
if ([string]$signature.Status -ne [string]$Authority.python.authenticode_status -or
    $subject -notlike "*$($Authority.python.publisher_subject_contains)*") {
    throw "KIS_PROJECT_PYTHON_INSTALLER_SIGNATURE_INVALID: status=$($signature.Status) subject=$subject"
}
Write-Host "Installer SHA256: $((Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash)"

$arguments = @(
    '/quiet',
    'InstallAllUsers=0',
    "TargetDir=$PythonRoot",
    'PrependPath=0',
    'AppendPath=0',
    'Include_launcher=0',
    'AssociateFiles=0',
    'Shortcuts=0',
    'Include_test=0',
    'Include_pip=1',
    'Include_dev=1',
    'Include_exe=1',
    'Include_lib=1',
    'Include_tools=1',
    'Include_tcltk=0'
)
$process = Start-Process -FilePath $Installer -ArgumentList $arguments -Wait -PassThru
if ($process.ExitCode -ne 0) {
    throw "KIS_PROJECT_PYTHON_INSTALL_FAILED: exit_code=$($process.ExitCode)"
}
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "KIS_PROJECT_PYTHON_INSTALL_MISSING: $PythonExe"
}
$runtime = Resolve-KisMcpProjectPython -Authority $Authority
Write-Host "Project Python installed and verified: $($runtime.executable)"
Write-Host "Base prefix: $($runtime.base_prefix)"
Write-Host "Acquisition evidence: $AcquisitionRoot"
