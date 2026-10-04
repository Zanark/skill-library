[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$inventoryPath = Join-Path $repoRoot 'source-inventory.json'
$expectedDocs = @(
    'README.md',
    'SKILL.md',
    'docs\ARCHITECTURE.md',
    'docs\WORKFLOW.md',
    'docs\REFERENCE.md',
    'docs\EXAMPLES.md',
    'docs\OPERATIONS-AND-TESTING.md'
)
$excludedNames = @(
    'daily-sev2-report',
    'DailySev2Report',
    'outage-comms-formatted',
    'OutageCommsFormatted',
    'dri-workplan'
)
$errors = [System.Collections.Generic.List[string]]::new()

if (-not (Test-Path -LiteralPath $inventoryPath)) {
    throw "Missing source inventory: $inventoryPath"
}

$inventory = Get-Content -Raw -LiteralPath $inventoryPath | ConvertFrom-Json

foreach ($entry in $inventory) {
    $skillRoot = Split-Path -Parent $entry.destination

    foreach ($relativePath in $expectedDocs) {
        $path = Join-Path $skillRoot $relativePath
        if (-not (Test-Path -LiteralPath $path)) {
            $errors.Add("Missing required file: $path")
        }
    }

    if (Test-Path -LiteralPath $entry.destination) {
        $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $entry.destination).Hash.ToLowerInvariant()
        if ($actualHash -ne $entry.sha256) {
            $errors.Add("Source hash mismatch for $($entry.name): expected $($entry.sha256), found $actualHash")
        }
    }
}

foreach ($excludedName in $excludedNames) {
    $excludedPath = Join-Path (Join-Path $repoRoot 'skills') $excludedName
    if (Test-Path -LiteralPath $excludedPath) {
        $errors.Add("Explicitly excluded skill is present: $excludedPath")
    }
}

$markdownFiles = Get-ChildItem -Path $repoRoot -Filter '*.md' -File -Recurse |
    Where-Object {
        $_.FullName -notmatch '\\.git\\' -and
        $_.Name -ne 'SKILL.md'
    }

foreach ($file in $markdownFiles) {
    $content = Get-Content -Raw -LiteralPath $file.FullName
    $visibleLines = [System.Collections.Generic.List[string]]::new()
    $activeFence = $null

    foreach ($line in ($content -split "`r?`n")) {
        if ($line -match '^\s*(`{3,}|~{3,})') {
            $marker = $Matches[1]
            if ($null -eq $activeFence) {
                $activeFence = $marker
            }
            elseif ($marker[0] -eq $activeFence[0] -and $marker.Length -ge $activeFence.Length) {
                $activeFence = $null
            }
            continue
        }

        if ($null -eq $activeFence) {
            $visibleLines.Add($line)
        }
    }

    $contentWithoutFences = $visibleLines -join "`n"
    $contentWithoutCode = [regex]::Replace(
        $contentWithoutFences,
        '`+[^`\r\n]*`+',
        ''
    )
    $links = [regex]::Matches(
        $contentWithoutCode,
        '\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+)\)'
    )

    foreach ($link in $links) {
        $rawTarget = $link.Groups[1].Value.Split('#')[0]
        if ([string]::IsNullOrWhiteSpace($rawTarget)) {
            continue
        }

        $decodedTarget = [uri]::UnescapeDataString($rawTarget)
        $targetPath = Join-Path $file.DirectoryName $decodedTarget
        if (-not (Test-Path -LiteralPath $targetPath)) {
            $errors.Add("Broken relative link in $($file.FullName): $rawTarget")
        }
    }
}

if ($errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Host "Skill library validation passed for $($inventory.Count) skills."
