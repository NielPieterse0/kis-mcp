[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string]$CodexExecutable = 'codex',

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ProjectPath
)

$ErrorActionPreference = 'Stop'

function Get-RepositoryStateFingerprint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepositoryPath,

        [Parameter(Mandatory = $true)]
        [string]$GitExecutable
    )

    $Head = @(& $GitExecutable -C $RepositoryPath rev-parse HEAD 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw 'CODEX_CLI_GIT_HEAD_FAILED'
    }
    $Status = @(& $GitExecutable -C $RepositoryPath status --porcelain=v1 --untracked-files=all 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw 'CODEX_CLI_GIT_STATUS_FAILED'
    }
    $Diff = @(& $GitExecutable -C $RepositoryPath diff --no-ext-diff --binary HEAD -- 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw 'CODEX_CLI_GIT_DIFF_FAILED'
    }
    $Untracked = @(& $GitExecutable -C $RepositoryPath ls-files --others --exclude-standard 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw 'CODEX_CLI_GIT_UNTRACKED_FAILED'
    }

    $UntrackedHashes = foreach ($RelativePath in ($Untracked | Sort-Object)) {
        $FullPath = Join-Path $RepositoryPath $RelativePath
        if (Test-Path -LiteralPath $FullPath -PathType Leaf) {
            "${RelativePath}:$((Get-FileHash -LiteralPath $FullPath -Algorithm SHA256).Hash)"
        }
    }
    $Document = [ordered]@{
        head = @($Head)
        status = @($Status)
        diff = @($Diff)
        untracked = @($UntrackedHashes)
    } | ConvertTo-Json -Depth 4 -Compress
    $Bytes = [System.Text.Encoding]::UTF8.GetBytes($Document)
    $Hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        return [Convert]::ToHexString($Hasher.ComputeHash($Bytes))
    }
    finally {
        $Hasher.Dispose()
    }
}

$ResolvedProject = (Resolve-Path -LiteralPath $ProjectPath).Path
if (-not (Test-Path -LiteralPath (Join-Path $ResolvedProject '.git'))) {
    throw "CODEX_CLI_PROJECT_NOT_GIT_REPOSITORY: $ResolvedProject"
}

$Prompt = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($Prompt)) {
    throw 'CODEX_CLI_PROMPT_REQUIRED'
}

$ResolvedCodex = (Get-Command $CodexExecutable -ErrorAction Stop).Source
$Arguments = @(
    'exec',
    '--ephemeral',
    '--json',
    '--sandbox',
    'read-only',
    '--color',
    'never',
    '-C',
    $ProjectPath,
    '-'
)

$ResolvedGit = (Get-Command git -ErrorAction Stop).Source
$BeforeFingerprint = Get-RepositoryStateFingerprint `
    -RepositoryPath $ResolvedProject `
    -GitExecutable $ResolvedGit

$Output = @($Prompt | & $ResolvedCodex @Arguments)
$CodexExitCode = $LASTEXITCODE

$AfterFingerprint = Get-RepositoryStateFingerprint `
    -RepositoryPath $ResolvedProject `
    -GitExecutable $ResolvedGit
if ($AfterFingerprint -ne $BeforeFingerprint) {
    [Console]::Error.WriteLine('CODEX_CLI_MUTATION_DETECTED')
    exit 86
}

foreach ($Line in $Output) {
    [Console]::Out.WriteLine($Line)
}
exit $CodexExitCode
