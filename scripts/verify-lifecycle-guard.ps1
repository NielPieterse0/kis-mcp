[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ChangeId,
    [Parameter(Mandatory)][string]$SourceSha,
    [Parameter(Mandatory)][string]$SourceTree,
    [string]$StateRoot = 'C:\Projects\.kis-mcp\once-through',
    [switch]$DiagnosticOverride
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($ChangeId -notmatch '^\d{3,}-[a-z0-9][a-z0-9-]*$') {
    throw 'LIFECYCLE_GUARD_CHANGE_ID_INVALID'
}
if ($SourceSha -cnotmatch '^[0-9a-f]{40}$') {
    throw 'LIFECYCLE_GUARD_SOURCE_SHA_INVALID'
}
if ($SourceTree -cnotmatch '^[0-9a-f]{40}$') {
    throw 'LIFECYCLE_GUARD_SOURCE_TREE_INVALID'
}

$StateRoot = [IO.Path]::GetFullPath($StateRoot)
$PromotionsRoot = Join-Path $StateRoot 'promotions'
$Matches = @()
if (Test-Path -LiteralPath $PromotionsRoot -PathType Container) {
    foreach ($Path in @(Get-ChildItem -LiteralPath $PromotionsRoot -Filter '*.json' -File)) {
        try {
            $Promotion = Get-Content -LiteralPath $Path.FullName -Raw | ConvertFrom-Json
        }
        catch {
            continue
        }
        if (
            [string]$Promotion.status -ceq 'promotion_ready' -and
            [string]$Promotion.change_id -ceq $ChangeId -and
            [string]$Promotion.source_commit_sha -ceq $SourceSha
        ) {
            $Matches += [pscustomobject]@{ Path = $Path.FullName; Promotion = $Promotion }
        }
    }
}
if ($Matches.Count -gt 1) {
    throw 'LIFECYCLE_GUARD_PROMOTION_AMBIGUOUS'
}

if ($Matches.Count -eq 0) {
    [ordered]@{
        schema_version = 1
        contract = 'change-lifecycle-guard-v1'
        disposition = 'allowed'
        lifecycle_blocked = $false
    } | ConvertTo-Json -Compress | Write-Output
    exit 0
}

$Selected = $Matches[0]
$Promotion = $Selected.Promotion
$StaleTree = $false
$RequiredTreeKinds = @('verification', 'review_closed')
$SeenTreeKinds = @{}
foreach ($Evidence in @($Promotion.evidence)) {
    $KindProperty = $Evidence.PSObject.Properties['kind']
    $Kind = if ($null -ne $KindProperty) { [string]$KindProperty.Value } else { '' }
    $ValidityProperty = $Evidence.PSObject.Properties['validity_inputs']
    $ValidityInputs = if ($null -ne $ValidityProperty) { $ValidityProperty.Value } else { $null }
    $TreeProperty = if ($null -ne $ValidityInputs) { $ValidityInputs.PSObject.Properties['tree'] } else { $null }
    if ($Kind -in $RequiredTreeKinds) {
        if (
            $null -eq $TreeProperty -or
            [string]$TreeProperty.Value -cnotmatch '^[0-9a-f]{40}$' -or
            [string]$TreeProperty.Value -cne $SourceTree
        ) {
            $StaleTree = $true
            break
        }
        $SeenTreeKinds[$Kind] = $true
    }
    elseif ($null -ne $TreeProperty -and [string]$TreeProperty.Value -cne $SourceTree) {
        $StaleTree = $true
        break
    }
}
if (@($RequiredTreeKinds | Where-Object { -not $SeenTreeKinds.ContainsKey($_) }).Count -gt 0) {
    $StaleTree = $true
}
if ($StaleTree) {
    [ordered]@{
        schema_version = 1
        contract = 'change-lifecycle-guard-v1'
        disposition = 'allowed'
        reason = 'PROMOTION_EVIDENCE_STALE'
        lifecycle_blocked = $false
    } | ConvertTo-Json -Compress | Write-Output
    exit 0
}

$TelemetryRoot = Join-Path $StateRoot 'lifecycle-telemetry'
[IO.Directory]::CreateDirectory($TelemetryRoot) | Out-Null
$EventName = if ($DiagnosticOverride) { 'diagnostic_override_used' } else { 'redundant_operation_prevented' }
$TelemetryPath = Join-Path $TelemetryRoot ("{0}-{1}.json" -f [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ'), [Guid]::NewGuid().ToString('N'))
$Telemetry = [ordered]@{
    schema_version = 1
    event = $EventName
    operation = 'run_local_full_verification'
    change_id = $ChangeId
    source_sha = $SourceSha
    source_tree = $SourceTree
    promotion_receipt = $Selected.Path
    diagnostic_override = [bool]$DiagnosticOverride
    observed_utc = [DateTime]::UtcNow.ToString('o')
}
$Temporary = "$TelemetryPath.next-$([Guid]::NewGuid().ToString('N'))"
[IO.File]::WriteAllText(
    $Temporary,
    ($Telemetry | ConvertTo-Json -Depth 6),
    [Text.UTF8Encoding]::new($false)
)
[IO.File]::Move($Temporary, $TelemetryPath)

$Payload = [ordered]@{
    schema_version = 1
    contract = 'change-lifecycle-guard-v1'
    code = 'REDUNDANT_VERIFICATION'
    disposition = if ($DiagnosticOverride) { 'diagnostic_only' } else { 'redundant' }
    lifecycle_blocked = $false
    next_required_action = 'converge_change_to_done'
    canonical_owner = 'github_actions_exact_pr_head'
    promotion_receipt = $Selected.Path
    diagnostic_override = [bool]$DiagnosticOverride
    existing_evidence = @(
        foreach ($Evidence in @($Promotion.evidence)) {
            [ordered]@{
                evidence_id = [string]$Evidence.evidence_id
                kind = [string]$Evidence.kind
                receipt_ref = if ($null -ne $Evidence.PSObject.Properties['receipt_ref']) { [string]$Evidence.receipt_ref } else { '' }
            }
        }
    )
}
$Payload | ConvertTo-Json -Depth 8 -Compress | Write-Output
if ($DiagnosticOverride) {
    exit 0
}
exit 23
