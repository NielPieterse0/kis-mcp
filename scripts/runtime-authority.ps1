$RuntimeAuthorityPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'settings\runtime-authority.settings.json'

function Get-KisMcpRuntimeAuthority {
    if (-not (Test-Path -LiteralPath $RuntimeAuthorityPath -PathType Leaf)) {
        throw "KIS_RUNTIME_AUTHORITY_MISSING: $RuntimeAuthorityPath"
    }
    $authority = Get-Content -LiteralPath $RuntimeAuthorityPath -Raw | ConvertFrom-Json
    if ([int]$authority.schema_version -ne 2) {
        throw 'KIS_RUNTIME_AUTHORITY_SCHEMA_INVALID: schema_version must be 2.'
    }
    if ([string]::IsNullOrWhiteSpace([string]$authority.project_boundary)) {
        throw 'KIS_RUNTIME_AUTHORITY_SCHEMA_INVALID: project_boundary is required.'
    }
    return $authority
}

function Assert-KisMcpAuthenticodeRuntime(
    [string]$Path,
    [string]$ExpectedStatus,
    [string]$PublisherSubjectContains,
    [string]$RuntimeName
) {
    $signature = Get-AuthenticodeSignature -LiteralPath $Path
    if ([string]$signature.Status -ne $ExpectedStatus) {
        throw "KIS_RUNTIME_SIGNATURE_INVALID: runtime=$RuntimeName path=$Path status=$($signature.Status)"
    }
    $subject = if ($null -ne $signature.SignerCertificate) {
        [string]$signature.SignerCertificate.Subject
    } else { '' }
    if ($subject -notlike "*$PublisherSubjectContains*") {
        throw "KIS_RUNTIME_PUBLISHER_INVALID: runtime=$RuntimeName path=$Path subject=$subject"
    }
    return [ordered]@{
        status = [string]$signature.Status
        subject = $subject
    }
}

function Test-KisMcpPathWithinBoundary([string]$Path, [string]$Boundary) {
    $fullPath = [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
    $fullBoundary = [System.IO.Path]::GetFullPath($Boundary).TrimEnd('\')
    return $fullPath.Equals($fullBoundary, [System.StringComparison]::OrdinalIgnoreCase) -or
        $fullPath.StartsWith($fullBoundary + '\', [System.StringComparison]::OrdinalIgnoreCase)
}

function Resolve-KisMcpProjectPython([object]$Authority = $(Get-KisMcpRuntimeAuthority)) {
    $resolved = [System.IO.Path]::GetFullPath([string]$Authority.python.executable)
    $boundary = [string]$Authority.project_boundary
    if (-not (Test-KisMcpPathWithinBoundary -Path $resolved -Boundary $boundary)) {
        throw "KIS_PROJECT_PYTHON_BOUNDARY_VIOLATION: executable=$resolved boundary=$boundary"
    }
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
        throw "KIS_PROJECT_PYTHON_MISSING: $resolved"
    }
    $runtime = (& $resolved -c "import json,sys; print(json.dumps({'version':'.'.join(map(str,sys.version_info[:3])),'major_minor':'.'.join(map(str,sys.version_info[:2])),'base_prefix':sys.base_prefix}))" | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0) {
        throw "KIS_PROJECT_PYTHON_INSPECTION_FAILED: $resolved"
    }
    if ([string]$runtime.version -ne [string]$Authority.python.version -or
        [string]$runtime.major_minor -ne [string]$Authority.python.major_minor) {
        throw "KIS_PROJECT_PYTHON_VERSION_INVALID: expected=$($Authority.python.version) actual=$($runtime.version)"
    }
    if (-not (Test-KisMcpPathWithinBoundary -Path ([string]$runtime.base_prefix) -Boundary $boundary)) {
        throw "KIS_PROJECT_PYTHON_BASE_BOUNDARY_VIOLATION: base_prefix=$($runtime.base_prefix) boundary=$boundary"
    }
    $signature = Assert-KisMcpAuthenticodeRuntime -Path $resolved `
        -ExpectedStatus ([string]$Authority.python.authenticode_status) `
        -PublisherSubjectContains ([string]$Authority.python.publisher_subject_contains) `
        -RuntimeName 'python'
    return [pscustomobject]@{
        executable = $resolved
        version = [string]$runtime.major_minor
        full_version = [string]$runtime.version
        base_prefix = [string]$runtime.base_prefix
        ownership = [string]$Authority.python.ownership
        signature_status = [string]$signature.status
        signer_subject = [string]$signature.subject
    }
}

function Assert-KisMcpProjectVenv([string]$PythonExecutable, [object]$Authority = $(Get-KisMcpRuntimeAuthority)) {
    $boundary = [string]$Authority.project_boundary
    $info = (& $PythonExecutable -c "import json,sys; print(json.dumps({'executable':sys.executable,'prefix':sys.prefix,'base_prefix':sys.base_prefix}))" | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0) {
        throw "KIS_VENV_INSPECTION_FAILED: $PythonExecutable"
    }
    foreach ($name in @('executable', 'prefix', 'base_prefix')) {
        $value = [string]$info.$name
        if (-not (Test-KisMcpPathWithinBoundary -Path $value -Boundary $boundary)) {
            throw "KIS_VENV_BOUNDARY_VIOLATION: field=$name value=$value boundary=$boundary"
        }
    }
    return $info
}

function Resolve-KisMcpUvRuntime([object]$Authority = $(Get-KisMcpRuntimeAuthority)) {
    $command = Get-Command ([string]$Authority.uv.command) -CommandType Application -ErrorAction Stop |
        Select-Object -First 1
    return [pscustomobject]@{
        executable = $command.Source
        ownership = [string]$Authority.uv.ownership
        acquisition_policy = [string]$Authority.uv.acquisition_policy
    }
}

function Resolve-KisMcpNodeRuntime([object]$Authority = $(Get-KisMcpRuntimeAuthority)) {
    $command = Get-Command ([string]$Authority.node.command) -CommandType Application -ErrorAction Stop |
        Select-Object -First 1
    $signature = Assert-KisMcpAuthenticodeRuntime -Path $command.Source `
        -ExpectedStatus ([string]$Authority.node.authenticode_status) `
        -PublisherSubjectContains ([string]$Authority.node.publisher_subject_contains) `
        -RuntimeName 'node'
    return [pscustomobject]@{
        executable = $command.Source
        ownership = [string]$Authority.node.ownership
        signature_status = [string]$signature.status
        signer_subject = [string]$signature.subject
        native_helpers_policy = [string]$Authority.node.native_helpers_policy
    }
}
