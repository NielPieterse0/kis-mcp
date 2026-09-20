[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$Name = 'kis-mcp-task-backend'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$RepositoryRoot = [IO.Path]::GetFullPath($RepositoryRoot)
$Settings = Get-Content -LiteralPath (Join-Path $RepositoryRoot 'settings\task-runtime.settings.json') -Raw | ConvertFrom-Json
$Image = [string]$Settings.backend_image
$BackendUri = [Uri]([string]$Settings.backend_url)
if ($BackendUri.Host -ne '127.0.0.1' -or $BackendUri.Scheme -ne 'redis') { throw 'KIS_MCP_TASK_BACKEND_URI_INVALID' }
$Port = $BackendUri.Port
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'KIS_MCP_TASK_BACKEND_PORT_INVALID' }
$Docker = (Get-Command docker -ErrorAction Stop).Source
& $Docker image inspect $Image *> $null
if ($LASTEXITCODE -ne 0) { throw "KIS_MCP_TASK_BACKEND_IMAGE_MISSING: $Image. Acquire it through an approved external path; this launcher never pulls." }
$existing = & $Docker ps -a --filter "name=^/$Name$" --format '{{.Names}}'
if ($existing -eq $Name) {
    if ((& $Docker ps --filter "name=^/$Name$" --format '{{.Names}}') -ne $Name) { & $Docker start $Name | Out-Null }
} else {
    & $Docker run -d --name $Name --restart unless-stopped -p "127.0.0.1:${Port}:6379" $Image valkey-server --save 60 1 --appendonly yes | Out-Null
}
& $Docker exec $Name valkey-cli ping
if ($LASTEXITCODE -ne 0) { throw 'KIS_MCP_TASK_BACKEND_HEALTH_FAILED' }
