Set-StrictMode -Version Latest

function Get-KisMcpProviderSecretBindings {
    param([Parameter(Mandatory)][string]$RepositoryRoot)

    $Bindings = @()
    $ProjectsPath = Join-Path $RepositoryRoot 'settings\projects.settings.json'
    $Projects = Get-Content -LiteralPath $ProjectsPath -Raw | ConvertFrom-Json
    foreach ($Project in @($Projects.projects)) {
        foreach ($Database in @($Project.databases)) {
            if ([string]$Database.boundary -ne 'external') { continue }
            $Reference = [string]$Database.secret_ref
            if ([string]::IsNullOrWhiteSpace($Reference)) {
                throw "KIS_MCP_DBHUB_SECRET_REFERENCE_MISSING: $($Project.project_id)/$($Database.binding_id)"
            }
            $ProjectName = ([string]$Project.project_id).Replace('-', '_').ToUpperInvariant()
            $BindingName = ([string]$Database.binding_id).Replace('-', '_').ToUpperInvariant()
            $Bindings += [pscustomobject]@{
                Environment = "KIS_MCP_DBHUB_${ProjectName}_${BindingName}_DSN"
                Reference = $Reference
            }
        }
    }

    $DockerPath = Join-Path $RepositoryRoot 'settings\providers\dockerhub.provider.json'
    $Docker = Get-Content -LiteralPath $DockerPath -Raw | ConvertFrom-Json
    if ([string]$Docker.auth.mode -eq 'pat') {
        $Reference = [string]$Docker.auth.secret_ref
        if ([string]::IsNullOrWhiteSpace($Reference)) {
            throw 'KIS_MCP_DOCKERHUB_SECRET_REFERENCE_MISSING'
        }
        $Bindings += [pscustomobject]@{
            Environment = 'KIS_MCP_DOCKERHUB_PAT'
            Reference = $Reference
        }
    }

    $Names = @($Bindings | ForEach-Object { [string]$_.Environment })
    if (@($Names | Sort-Object -Unique).Count -ne $Names.Count) {
        throw 'KIS_MCP_PROVIDER_SECRET_ENVIRONMENT_DUPLICATE'
    }
    return @($Bindings)
}

function Resolve-KisMcpProviderSecretEnvironmentFromPayload {
    param(
        [Parameter(Mandatory)][string]$RepositoryRoot,
        [Parameter(Mandatory)][hashtable]$SecurePayload
    )
    $Environment = @{}
    foreach ($Binding in @(Get-KisMcpProviderSecretBindings -RepositoryRoot $RepositoryRoot)) {
        $Value = Resolve-KisMcpSecretInternal `
            -Reference ([string]$Binding.Reference) `
            -SecurePayload $SecurePayload
        if ([string]::IsNullOrWhiteSpace($Value)) {
            throw "KIS_MCP_PROVIDER_SECRET_VALUE_MISSING: $($Binding.Reference)"
        }
        $Environment[[string]$Binding.Environment] = $Value
        $Value = $null
    }
    return $Environment
}

function Resolve-KisMcpProviderSecretEnvironment {
    param([Parameter(Mandatory)][string]$RepositoryRoot)

    $Bindings = @(Get-KisMcpProviderSecretBindings -RepositoryRoot $RepositoryRoot)
    $Environment = @{}
    if ($Bindings.Count -eq 0) { return $Environment }

    $CredentialTarget = Get-KisMcpRuntimeUnlockCredentialTarget
    $Credential = $null
    $Payload = @{}
    try {
        try {
            $Credential = Get-KisMcpWindowsCredential -Target $CredentialTarget
        }
        catch {
            throw 'KIS_MCP_PROVIDER_SECRET_RUNTIME_UNLOCK_MISSING: run scripts\configure-secret-runtime-unlock.ps1.'
        }
        $Payload['unlock'] = $Credential
        $Credential = $null
        try {
            $null = Invoke-KisMcpSecretCommand `
                -CommandArguments @('verify-unlock') `
                -SecurePayload $Payload
        }
        catch {
            throw 'KIS_MCP_PROVIDER_SECRET_RUNTIME_UNLOCK_INVALID: refresh the runtime unlock credential.'
        }
        foreach ($Binding in $Bindings) {
            $Value = Resolve-KisMcpSecretInternal `
                -Reference ([string]$Binding.Reference) `
                -SecurePayload $Payload
            if ([string]::IsNullOrWhiteSpace($Value)) {
                throw "KIS_MCP_PROVIDER_SECRET_VALUE_MISSING: $($Binding.Reference)"
            }
            $Environment[[string]$Binding.Environment] = $Value
            $Value = $null
        }
        return $Environment
    }
    finally {
        if ($null -ne $Payload) { $Payload.Clear() }
        $Credential = $null
        $CredentialTarget = $null
    }
}

function Clear-KisMcpProviderSecretEnvironment {
    param([hashtable]$Environment)
    if ($null -eq $Environment) { return }
    foreach ($Name in @($Environment.Keys)) {
        $Environment[$Name] = $null
        $Environment.Remove($Name)
    }
    $Environment.Clear()
}
