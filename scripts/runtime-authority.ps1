$RuntimeAuthorityPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'settings\runtime-authority.settings.json'

function Get-KisMcpRuntimeAuthority {
    if (-not (Test-Path -LiteralPath $RuntimeAuthorityPath -PathType Leaf)) {
        throw "KIS_RUNTIME_AUTHORITY_MISSING: $RuntimeAuthorityPath"
    }
    $authority = Get-Content -LiteralPath $RuntimeAuthorityPath -Raw | ConvertFrom-Json
    if ([int]$authority.schema_version -ne 1) {
        throw 'KIS_RUNTIME_AUTHORITY_SCHEMA_INVALID: schema_version must be 1.'
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

function Resolve-KisMcpSystemPython([object]$Authority = $(Get-KisMcpRuntimeAuthority)) {
    $launcher = Get-Command ([string]$Authority.python.launcher) -CommandType Application -ErrorAction Stop |
        Select-Object -First 1
    $selector = [string]$Authority.python.selector
    $resolved = (& $launcher.Source $selector -c 'import sys; print(sys.executable)' 2>&1 | Select-Object -Last 1).Trim()
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
        throw "KIS_SYSTEM_PYTHON_RESOLUTION_FAILED: selector=$selector resolved=$resolved"
    }
    $version = (& $resolved -c "import sys; print('%s.%s' % sys.version_info[:2])").Trim()
    if ($LASTEXITCODE -ne 0 -or $version -ne [string]$Authority.python.major_minor) {
        throw "KIS_SYSTEM_PYTHON_VERSION_INVALID: expected=$($Authority.python.major_minor) actual=$version"
    }
    $signature = Assert-KisMcpAuthenticodeRuntime -Path $resolved `
        -ExpectedStatus ([string]$Authority.python.authenticode_status) `
        -PublisherSubjectContains ([string]$Authority.python.publisher_subject_contains) `
        -RuntimeName 'python'
    return [pscustomobject]@{
        executable = $resolved
        version = $version
        ownership = [string]$Authority.python.ownership
        signature_status = [string]$signature.status
        signer_subject = [string]$signature.subject
    }
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
