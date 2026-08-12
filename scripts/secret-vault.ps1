Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:KisMcpRepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$script:KisMcpPython = 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe'
$script:KisMcpSecretsSettingsPath = Join-Path $script:KisMcpRepositoryRoot 'settings\secrets.settings.json'
$script:KisMcpSecretsSettings = Get-Content -LiteralPath $script:KisMcpSecretsSettingsPath -Raw | ConvertFrom-Json
if ($script:KisMcpSecretsSettings.schema_version -ne 1) {
    throw 'KIS_MCP_SECRET_SETTINGS_VERSION_UNSUPPORTED'
}
$script:KisMcpSecretsRoot = [string]$script:KisMcpSecretsSettings.root
$script:KisMcpBootstrapEnvironment = [string]$script:KisMcpSecretsSettings.bootstrap_environment
$script:KisMcpSecretPipeEnvironment = 'KIS_MCP_SECRET_INPUT_PIPE_HANDLE'

function Get-KisMcpRuntimeUnlockCredentialTarget {
    $RuntimeUnlock = $script:KisMcpSecretsSettings.runtime_unlock
    if ($null -eq $RuntimeUnlock -or [string]$RuntimeUnlock.mode -ne 'windows-credential') {
        throw 'KIS_MCP_RUNTIME_UNLOCK_MODE_INVALID'
    }
    $Target = [string]$RuntimeUnlock.target
    if ([string]::IsNullOrWhiteSpace($Target) -or -not $Target.StartsWith('kis-mcp/secrets/', [StringComparison]::Ordinal)) {
        throw 'KIS_MCP_RUNTIME_UNLOCK_TARGET_INVALID'
    }
    return $Target
}

function Assert-KisMcpSecretsRuntime {
    if (-not (Test-Path -LiteralPath $script:KisMcpPython -PathType Leaf)) {
        throw "KIS_MCP_PYTHON_MISSING: $script:KisMcpPython"
    }
    if (-not $script:KisMcpSecretsRoot.StartsWith('C:\Projects\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'KIS_MCP_SECRET_ROOT_OUTSIDE_PROJECT_BOUNDARY'
    }
}

function Get-KisMcpUnlockPayload {
    param([string]$Prompt = 'Unlock kis-mcp secrets')

    if ([Environment]::GetEnvironmentVariable(
        $script:KisMcpBootstrapEnvironment,
        [EnvironmentVariableTarget]::Process
    )) {
        return @{}
    }
    $Unlock = Read-Host $Prompt -AsSecureString
    return @{ unlock = $Unlock }
}

function Read-KisMcpSecureValue {
    param([Parameter(Mandatory)][string]$Prompt)

    return Read-Host $Prompt -AsSecureString
}

function ConvertTo-KisMcpSecretInputJson {
    param([hashtable]$SecurePayload = @{})

    $PlainPayload = [ordered]@{}
    try {
        foreach ($Name in $SecurePayload.Keys) {
            $Value = $SecurePayload[$Name]
            if ($Value -is [Security.SecureString]) {
                $Pointer = [IntPtr]::Zero
                try {
                    $Pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
                    $PlainPayload[$Name] = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Pointer)
                }
                finally {
                    if ($Pointer -ne [IntPtr]::Zero) {
                        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Pointer)
                    }
                }
            }
            elseif ($Value -is [string]) {
                $PlainPayload[$Name] = $Value
            }
            else {
                throw "KIS_MCP_SECRET_INPUT_TYPE_INVALID: $Name"
            }
        }
        return ($PlainPayload | ConvertTo-Json -Compress -Depth 4)
    }
    finally {
        foreach ($Name in @($PlainPayload.Keys)) {
            $PlainPayload[$Name] = $null
        }
        $PlainPayload.Clear()
    }
}

function New-KisMcpSecretCliStartInfo {
    param([Parameter(Mandatory)][string[]]$CommandArguments)

    Assert-KisMcpSecretsRuntime
    $Info = [System.Diagnostics.ProcessStartInfo]::new()
    $Info.FileName = $script:KisMcpPython
    $Info.WorkingDirectory = $script:KisMcpRepositoryRoot
    $Info.UseShellExecute = $false
    $Info.CreateNoWindow = $true
    $Info.RedirectStandardInput = $true
    $Info.RedirectStandardOutput = $true
    $Info.RedirectStandardError = $true
    foreach ($Argument in @('-m', 'kis_mcp.secrets.cli') + $CommandArguments) {
        $Info.ArgumentList.Add($Argument)
    }
    $Info.Environment['PYTHONPATH'] = Join-Path $script:KisMcpRepositoryRoot 'src'
    $Info.Environment['KIS_MCP_SECRETS_ROOT'] = $script:KisMcpSecretsRoot
    return $Info
}

function Invoke-KisMcpSecretCommand {
    param(
        [Parameter(Mandatory)][string[]]$CommandArguments,
        [hashtable]$SecurePayload = @{},
        [switch]$RawOutput
    )

    $Info = New-KisMcpSecretCliStartInfo -CommandArguments $CommandArguments
    $Process = [System.Diagnostics.Process]::new()
    $Process.StartInfo = $Info
    if (-not $Process.Start()) {
        throw 'KIS_MCP_SECRET_COMMAND_START_FAILED'
    }

    $InputJson = ConvertTo-KisMcpSecretInputJson -SecurePayload $SecurePayload
    try {
        $StandardOutputTask = $Process.StandardOutput.ReadToEndAsync()
        $StandardErrorTask = $Process.StandardError.ReadToEndAsync()
        $Process.StandardInput.Write($InputJson)
        $Process.StandardInput.Close()
        $Process.WaitForExit()
        $StandardOutput = $StandardOutputTask.GetAwaiter().GetResult()
        $StandardError = $StandardErrorTask.GetAwaiter().GetResult()
        if ($Process.ExitCode -ne 0) {
            $SafeError = $StandardError.Trim()
            if (-not $SafeError) {
                $SafeError = "exit_code=$($Process.ExitCode)"
            }
            throw "KIS_MCP_SECRET_COMMAND_FAILED: $SafeError"
        }
        if ($RawOutput) {
            return $StandardOutput
        }
        return $StandardOutput.Trim()
    }
    finally {
        $InputJson = $null
        $Process.Dispose()
    }
}

function Assert-KisMcpSecureStringsMatch {
    param(
        [Parameter(Mandatory)][Security.SecureString]$First,
        [Parameter(Mandatory)][Security.SecureString]$Second
    )

    $FirstPointer = [IntPtr]::Zero
    $SecondPointer = [IntPtr]::Zero
    $FirstPlain = $null
    $SecondPlain = $null
    try {
        $FirstPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($First)
        $SecondPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Second)
        $FirstPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($FirstPointer)
        $SecondPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($SecondPointer)
        if (-not [String]::Equals($FirstPlain, $SecondPlain, [StringComparison]::Ordinal)) {
            throw 'KIS_MCP_SECRET_CONFIRMATION_MISMATCH'
        }
    }
    finally {
        $FirstPlain = $null
        $SecondPlain = $null
        if ($FirstPointer -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($FirstPointer)
        }
        if ($SecondPointer -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($SecondPointer)
        }
    }
}

function Invoke-KisMcpPostRotationRuntimeCredentialUpdate {
    [CmdletBinding()]
    param([Parameter(Mandatory)][scriptblock]$Action)

    try {
        & $Action
    }
    catch {
        throw 'KIS_MCP_ROTATION_RUNTIME_CREDENTIAL_UPDATE_FAILED: vault rotation succeeded but the runtime credential update failed. Run scripts\configure-secret-runtime-unlock.ps1 using the new unlock before starting kis-mcp.'
    }
}

function Start-KisMcpSecretAwareProcess {
    param(
        [Parameter(Mandatory)][System.Diagnostics.ProcessStartInfo]$StartInfo,
        [hashtable]$SecurePayload = @{}
    )

    $Pipe = [System.IO.Pipes.AnonymousPipeServerStream]::new(
        [System.IO.Pipes.PipeDirection]::Out,
        [System.IO.HandleInheritability]::Inheritable
    )
    $StartInfo.Environment[$script:KisMcpSecretPipeEnvironment] = $Pipe.GetClientHandleAsString()
    $Process = [System.Diagnostics.Process]::new()
    $Process.StartInfo = $StartInfo
    $Started = $false
    $InputJson = $null
    try {
        if (-not $Process.Start()) {
            throw 'KIS_MCP_SECRET_RUNTIME_START_FAILED'
        }
        $Started = $true
        $Pipe.DisposeLocalCopyOfClientHandle()
        $InputJson = ConvertTo-KisMcpSecretInputJson -SecurePayload $SecurePayload
        $Writer = [System.IO.StreamWriter]::new(
            $Pipe,
            [System.Text.UTF8Encoding]::new($false),
            1024,
            $false
        )
        try {
            $Writer.Write($InputJson)
            $Writer.Flush()
        }
        finally {
            $Writer.Dispose()
        }
        return $Process
    }
    catch {
        if ($Started -and -not $Process.HasExited) {
            $Process.Kill()
            $Process.WaitForExit()
        }
        $Process.Dispose()
        throw
    }
    finally {
        $InputJson = $null
        $Pipe.Dispose()
    }
}

function Resolve-KisMcpSecretInternal {
    param(
        [Parameter(Mandatory)][string]$Reference,
        [hashtable]$SecurePayload = @{}
    )

    return Invoke-KisMcpSecretCommand `
        -CommandArguments @('resolve-internal', '--reference', $Reference) `
        -SecurePayload $SecurePayload `
        -RawOutput
}
