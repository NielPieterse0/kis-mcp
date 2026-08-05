[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$files = @(
    git ls-files --cached --others --exclude-standard "*.md" |
        Where-Object { $_ -and $_ -notmatch '^\.work/worktrees/' } |
        Sort-Object -Unique
)

$categories = [ordered]@{
    authorities = 0
    local_skills = 0
    change_records = 0
    development_evidence = 0
    other = 0
}

$missingLinks = [System.Collections.Generic.List[object]]::new()
$headingIssues = [System.Collections.Generic.List[object]]::new()

foreach ($file in $files) {
    if ($file -in @("AGENTS.md", "README.md", "SPEC.md") -or $file -match '^docs/[^/]+\.md$') {
        $categories.authorities++
    }
    elseif ($file -like ".agents/skills/*") {
        $categories.local_skills++
    }
    elseif ($file -like ".work/changes/*") {
        $categories.change_records++
    }
    elseif ($file -like "docs/development/*") {
        $categories.development_evidence++
    }
    else {
        $categories.other++
    }

    $text = Get-Content -LiteralPath $file -Raw
    $withoutFences = [regex]::Replace($text, '(?ms)^```.*?^```\s*$', '')
    $h1Count = ([regex]::Matches($withoutFences, '(?m)^# [^#].*$')).Count
    if ($h1Count -ne 1) {
        $headingIssues.Add([ordered]@{
            file = $file
            issue = "h1_count"
            value = $h1Count
        })
    }

    foreach ($match in [regex]::Matches($withoutFences, '\[[^\]]*\]\(([^)]+)\)')) {
        $target = $match.Groups[1].Value.Trim()
        if ($target -match '^(https?://|mailto:|#|<)') {
            continue
        }

        $targetPath = ($target -split '#', 2)[0]
        if ([string]::IsNullOrWhiteSpace($targetPath)) {
            continue
        }

        $decoded = [uri]::UnescapeDataString($targetPath)
        $base = Split-Path -Parent $file
        if ([string]::IsNullOrEmpty($base)) {
            $base = "."
        }
        $resolved = Join-Path $base $decoded
        if (-not (Test-Path -LiteralPath $resolved)) {
            $missingLinks.Add([ordered]@{
                file = $file
                target = $target
            })
        }
    }
}

$result = [ordered]@{
    markdown_count = $files.Count
    categories = $categories
    missing_relative_links = $missingLinks.Count
    missing_link_details = @($missingLinks)
    heading_issues = $headingIssues.Count
    heading_issue_details = @($headingIssues)
    limitations = @(
        "External URL availability was not checked.",
        "Markdown heading anchors were not resolved.",
        "Inline HTML links were not parsed."
    )
}

$result | ConvertTo-Json -Depth 6
